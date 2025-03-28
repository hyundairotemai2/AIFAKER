"""
StarGAN v2
Copyright (c) 2020-present NAVER Corp.

This work is licensed under the Creative Commons Attribution-NonCommercial
4.0 International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to
Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
"""
import os
from os.path import join as ospj
import time
import datetime
from munch import Munch

import torch
import torch.nn as nn
import torch.nn.functional as F

from core.model import build_model
from core.checkpoint import CheckpointIO
from core.data_loader import InputFetcher
import core.utils as utils
from metrics.eval import calculate_metrics

import lpips

def adversarial_input_attack_with_lpips_and_style(
    nets, x, s_ref, y_ref, lpips_model,
    epsilon=0.05, alpha=0.01, num_iter=10,
    lam_transfer=1.0, lam_vis=10.0, lam_lpips=5.0, lam_style=5.0
):
    device = x.device
    generator = nets.generator.module if isinstance(nets.generator, torch.nn.DataParallel) else nets.generator
    style_encoder = nets.style_encoder.module if isinstance(nets.style_encoder, torch.nn.DataParallel) else nets.style_encoder

    x_orig = x.detach()
    x_adv = x.clone().detach() + 0.001 * torch.randn_like(x)
    x_adv.requires_grad_(True)

    s_ref = s_ref.detach()
    s_ref_ = s_ref[0].unsqueeze(0).repeat(x.size(0), 1)

    for _ in range(num_iter):
        if x_adv.grad is not None:
            x_adv.grad.zero_()

        # 생성 결과
        x_fake = generator(x, s_ref_).detach()
        x_fake_adv = generator(x_adv, s_ref_)

        # 스타일 추정
        s_pred = style_encoder(x_fake, y_ref)
        s_pred_adv = style_encoder(x_fake_adv, y_ref)

        # normalize for LPIPS
        x_adv_norm = (x_adv - 0.5) * 2
        x_orig_norm = (x_orig - 0.5) * 2

        # 개별 loss
        loss_transfer = F.mse_loss(x_fake_adv, x_fake)                             # 생성 차이
        loss_lpips    = lpips_model(x_adv_norm, x_orig_norm).mean()               # 시각 유사성 (perceptual)
        loss_vis      = F.mse_loss(x_adv, x_orig)                                  # 픽셀 유사성
        loss_style    = -F.cosine_similarity(s_pred, s_pred_adv, dim=1).mean()     # 스타일 교란 (maximize distance)

        # 전체 loss
        total_loss = (
            lam_transfer * loss_transfer +
            lam_lpips * loss_lpips +
            lam_vis * loss_vis +
            lam_style * loss_style
        )

        total_loss.backward()

        with torch.no_grad():
            grad = x_adv.grad.sign()
            x_adv = x_adv + alpha * grad
            x_adv = torch.clamp(x_adv, x_orig - epsilon, x_orig + epsilon)
            x_adv.requires_grad_(True)

    return x_adv.detach()


class Solver(nn.Module):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.nets, self.nets_ema = build_model(args)
        # below setattrs are to make networks be children of Solver, e.g., for self.to(self.device)
        for name, module in self.nets.items():
            utils.print_network(module, name)
            setattr(self, name, module)
        for name, module in self.nets_ema.items():
            setattr(self, name + '_ema', module)

        if args.mode == 'train':
            self.optims = Munch()
            for net in self.nets.keys():
                if net == 'fan':
                    continue
                self.optims[net] = torch.optim.Adam(
                    params=self.nets[net].parameters(),
                    lr=args.f_lr if net == 'mapping_network' else args.lr,
                    betas=[args.beta1, args.beta2],
                    weight_decay=args.weight_decay)

            self.ckptios = [
                CheckpointIO(ospj(args.checkpoint_dir, '{:06d}_nets.ckpt'), data_parallel=True, **self.nets),
                CheckpointIO(ospj(args.checkpoint_dir, '{:06d}_nets_ema.ckpt'), data_parallel=True, **self.nets_ema),
                CheckpointIO(ospj(args.checkpoint_dir, '{:06d}_optims.ckpt'), **self.optims)]
        else:
            self.ckptios = [CheckpointIO(ospj(args.checkpoint_dir, '{:06d}_nets_ema.ckpt'), data_parallel=True, **self.nets_ema)]

        self.to(self.device)
        for name, network in self.named_children():
            # Do not initialize the FAN parameters
            if ('ema' not in name) and ('fan' not in name):
                print('Initializing %s...' % name)
                network.apply(utils.he_init)

    def _save_checkpoint(self, step):
        for ckptio in self.ckptios:
            ckptio.save(step)

    def _load_checkpoint(self, step):
        for ckptio in self.ckptios:
            ckptio.load(step)

    def _reset_grad(self):
        for optim in self.optims.values():
            optim.zero_grad()

    def train(self, loaders):
        args = self.args
        nets = self.nets
        nets_ema = self.nets_ema
        optims = self.optims

        # fetch random validation images for debugging
        fetcher = InputFetcher(loaders.src, loaders.ref, args.latent_dim, 'train')
        fetcher_val = InputFetcher(loaders.val, None, args.latent_dim, 'val')
        inputs_val = next(fetcher_val)

        # resume training if necessary
        if args.resume_iter > 0:
            self._load_checkpoint(args.resume_iter)

        # remember the initial value of ds weight
        initial_lambda_ds = args.lambda_ds

        print('Start training...')
        start_time = time.time()
        for i in range(args.resume_iter, args.total_iters):
            # fetch images and labels
            inputs = next(fetcher)
            x_real, y_org = inputs.x_src, inputs.y_src
            x_ref, x_ref2, y_trg = inputs.x_ref, inputs.x_ref2, inputs.y_ref
            z_trg, z_trg2 = inputs.z_trg, inputs.z_trg2

            masks = nets.fan.get_heatmap(x_real) if args.w_hpf > 0 else None

            # train the discriminator
            d_loss, d_losses_latent = compute_d_loss(
                nets, args, x_real, y_org, y_trg, z_trg=z_trg, masks=masks)
            self._reset_grad()
            d_loss.backward()
            optims.discriminator.step()

            d_loss, d_losses_ref = compute_d_loss(
                nets, args, x_real, y_org, y_trg, x_ref=x_ref, masks=masks)
            self._reset_grad()
            d_loss.backward()
            optims.discriminator.step()

            # train the generator
            g_loss, g_losses_latent = compute_g_loss(
                nets, args, x_real, y_org, y_trg, z_trgs=[z_trg, z_trg2], masks=masks)
            self._reset_grad()
            g_loss.backward()
            optims.generator.step()
            optims.mapping_network.step()
            optims.style_encoder.step()

            g_loss, g_losses_ref = compute_g_loss(
                nets, args, x_real, y_org, y_trg, x_refs=[x_ref, x_ref2], masks=masks)
            self._reset_grad()
            g_loss.backward()
            optims.generator.step()

            # compute moving average of network parameters
            moving_average(nets.generator, nets_ema.generator, beta=0.999)
            moving_average(nets.mapping_network, nets_ema.mapping_network, beta=0.999)
            moving_average(nets.style_encoder, nets_ema.style_encoder, beta=0.999)

            # decay weight for diversity sensitive loss
            if args.lambda_ds > 0:
                args.lambda_ds -= (initial_lambda_ds / args.ds_iter)

            # print out log info
            if (i+1) % args.print_every == 0:
                elapsed = time.time() - start_time
                elapsed = str(datetime.timedelta(seconds=elapsed))[:-7]
                log = "Elapsed time [%s], Iteration [%i/%i], " % (elapsed, i+1, args.total_iters)
                all_losses = dict()
                for loss, prefix in zip([d_losses_latent, d_losses_ref, g_losses_latent, g_losses_ref],
                                        ['D/latent_', 'D/ref_', 'G/latent_', 'G/ref_']):
                    for key, value in loss.items():
                        all_losses[prefix + key] = value
                all_losses['G/lambda_ds'] = args.lambda_ds
                log += ' '.join(['%s: [%.4f]' % (key, value) for key, value in all_losses.items()])
                print(log)

            # generate images for debugging
            if (i+1) % args.sample_every == 0:
                os.makedirs(args.sample_dir, exist_ok=True)
                utils.debug_image(nets_ema, args, inputs=inputs_val, step=i+1)

            # save model checkpoints
            if (i+1) % args.save_every == 0:
                self._save_checkpoint(step=i+1)

            # compute FID and LPIPS if necessary
            if (i+1) % args.eval_every == 0:
                calculate_metrics(nets_ema, args, i+1, mode='latent')
                calculate_metrics(nets_ema, args, i+1, mode='reference')

    #@torch.no_grad()
    def sample(self, loaders):
        args = self.args
        nets_ema = self.nets_ema
        device = self.device
        os.makedirs(args.result_dir, exist_ok=True)
        self._load_checkpoint(args.resume_iter)

        nets_ema.generator.eval()
        nets_ema.mapping_network.eval()
        nets_ema.style_encoder.eval()

        # ✅ LPIPS 모델 불러오기
        lpips_model = lpips.LPIPS(net='alex').to(device)
        lpips_model.eval()

        # 🔄 도메인 y가 다른 ref 얻기
        while True:
            src = next(InputFetcher(loaders.src, None, args.latent_dim, 'test'))
            ref = next(InputFetcher(loaders.ref, None, args.latent_dim, 'test'))
            if not torch.equal(src.y, ref.y):
                break

        s_ref = nets_ema.style_encoder(ref.x, ref.y)

        fname_org = ospj(args.result_dir, 'reference.jpg')
        print('Working on {}...'.format(fname_org))
        utils.translate_using_reference(nets_ema, args, src.x, ref.x, ref.y, fname_org)

        print("Applying Feature Space Attack on input images...")
        try:
            x_adv = adversarial_input_attack_with_lpips_and_style(
            nets_ema, src.x, s_ref, src.y, lpips_model,
            epsilon=0.1, alpha=0.02, num_iter=20,
            lam_transfer=0.3, lam_vis=2.0, lam_lpips=1.0, lam_style=15.0
        )
        except RuntimeError as e:
            print(f"❌ Feature Space Attack 실패: {e}")
            return

        fname_adv = ospj(args.result_dir, 'adversarial_result_lpips.jpg')
        utils.translate_using_reference(nets_ema, args, x_adv, ref.x, ref.y, fname_adv)
        print("✅ Sample complete. Saved to:", fname_adv)

        with torch.no_grad():
            s_ref_eval = s_ref[0].unsqueeze(0).repeat(src.x.size(0), 1)
            
            # 1. Generator Output
            x_fake = nets_ema.generator(src.x, s_ref_eval)
            x_fake_adv = nets_ema.generator(x_adv, s_ref_eval)

            # 2. LPIPS (Perceptual similarity between outputs)
            x_fake_norm = (x_fake - 0.5) * 2
            x_fake_adv_norm = (x_fake_adv - 0.5) * 2
            lpips_score = lpips_model(x_fake_norm, x_fake_adv_norm).mean().item()

            # 3. Input space similarity
            mse_input = F.mse_loss(src.x, x_adv).item()

            # 4. Generator output similarity (pixel-wise)
            mse_output = F.mse_loss(x_fake, x_fake_adv).item()

            # 5. Style consistency
            s_src = nets_ema.style_encoder(src.x, src.y)
            s_adv = nets_ema.style_encoder(x_adv, src.y)
            cos_sim = F.cosine_similarity(s_src, s_adv, dim=1).mean().item()

        # 📢 Print Evaluation Summary
        print(f"🔍 MSE(x, x_adv): {mse_input:.6f}")
        print(f"🎯 MSE(G(x), G(x_adv)): {mse_output:.6f}")
        print(f"✨ LPIPS(G(x), G(x_adv)): {lpips_score:.6f}")
        print(f"🎨 Cosine similarity(style_x, style_x_adv): {cos_sim:.6f}")
        x_vis_list = []
        for i in range(src.x.size(0)):
            x_orig_i = src.x[i:i+1]   # (1, C, H, W)
            x_adv_i  = x_adv[i:i+1]   # (1, C, H, W)
            x_vis_list.append(torch.cat([x_orig_i, x_adv_i], dim=0))  # (2, C, H, W)

        # (2*batch, C, H, W)로 concat 후 저장
        x_vis_grid = torch.cat(x_vis_list, dim=0)
        x_comp_path = ospj(args.result_dir, 'x_comparison.jpg')
        utils.save_image(x_vis_grid, ncol=2, filename=x_comp_path)
        print(f"✅ Input vs Adv image comparison saved to: {x_comp_path}")
        #fname = ospj(args.result_dir, 'video_ref.mp4')
        #print('Working on {}...'.format(fname))
        #utils.video_ref(nets_ema, args, src.x, ref.x, ref.y, fname)

    @torch.no_grad()
    def evaluate(self):
        args = self.args
        nets_ema = self.nets_ema
        resume_iter = args.resume_iter
        self._load_checkpoint(args.resume_iter)
        calculate_metrics(nets_ema, args, step=resume_iter, mode='latent')
        calculate_metrics(nets_ema, args, step=resume_iter, mode='reference')


def compute_d_loss(nets, args, x_real, y_org, y_trg, z_trg=None, x_ref=None, masks=None):
    assert (z_trg is None) != (x_ref is None)
    # with real images
    x_real.requires_grad_()
    out = nets.discriminator(x_real, y_org)
    loss_real = adv_loss(out, 1)
    loss_reg = r1_reg(out, x_real)

    # with fake images
    with torch.no_grad():
        if z_trg is not None:
            s_trg = nets.mapping_network(z_trg, y_trg)
        else:  # x_ref is not None
            s_trg = nets.style_encoder(x_ref, y_trg)

        x_fake = nets.generator(x_real, s_trg, masks=masks)
    out = nets.discriminator(x_fake, y_trg)
    loss_fake = adv_loss(out, 0)

    loss = loss_real + loss_fake + args.lambda_reg * loss_reg
    return loss, Munch(real=loss_real.item(),
                       fake=loss_fake.item(),
                       reg=loss_reg.item())


def compute_g_loss(nets, args, x_real, y_org, y_trg, z_trgs=None, x_refs=None, masks=None):
    assert (z_trgs is None) != (x_refs is None)
    if z_trgs is not None:
        z_trg, z_trg2 = z_trgs
    if x_refs is not None:
        x_ref, x_ref2 = x_refs

    # adversarial loss
    if z_trgs is not None:
        s_trg = nets.mapping_network(z_trg, y_trg)
    else:
        s_trg = nets.style_encoder(x_ref, y_trg)

    x_fake = nets.generator(x_real, s_trg, masks=masks)
    out = nets.discriminator(x_fake, y_trg)
    loss_adv = adv_loss(out, 1)

    # style reconstruction loss
    s_pred = nets.style_encoder(x_fake, y_trg)
    loss_sty = torch.mean(torch.abs(s_pred - s_trg))

    # diversity sensitive loss
    if z_trgs is not None:
        s_trg2 = nets.mapping_network(z_trg2, y_trg)
    else:
        s_trg2 = nets.style_encoder(x_ref2, y_trg)
    x_fake2 = nets.generator(x_real, s_trg2, masks=masks)
    x_fake2 = x_fake2.detach()
    loss_ds = torch.mean(torch.abs(x_fake - x_fake2))

    # cycle-consistency loss
    masks = nets.fan.get_heatmap(x_fake) if args.w_hpf > 0 else None
    s_org = nets.style_encoder(x_real, y_org)
    x_rec = nets.generator(x_fake, s_org, masks=masks)
    loss_cyc = torch.mean(torch.abs(x_rec - x_real))

    loss = loss_adv + args.lambda_sty * loss_sty \
        - args.lambda_ds * loss_ds + args.lambda_cyc * loss_cyc
    return loss, Munch(adv=loss_adv.item(),
                       sty=loss_sty.item(),
                       ds=loss_ds.item(),
                       cyc=loss_cyc.item())


def moving_average(model, model_test, beta=0.999):
    for param, param_test in zip(model.parameters(), model_test.parameters()):
        param_test.data = torch.lerp(param.data, param_test.data, beta)


def adv_loss(logits, target):
    assert target in [1, 0]
    targets = torch.full_like(logits, fill_value=target)
    loss = F.binary_cross_entropy_with_logits(logits, targets)
    return loss


def r1_reg(d_out, x_in):
    # zero-centered gradient penalty for real images
    batch_size = x_in.size(0)
    grad_dout = torch.autograd.grad(
        outputs=d_out.sum(), inputs=x_in,
        create_graph=True, retain_graph=True, only_inputs=True
    )[0]
    grad_dout2 = grad_dout.pow(2)
    assert(grad_dout2.size() == x_in.size())
    reg = 0.5 * grad_dout2.view(batch_size, -1).sum(1).mean(0)
    return reg