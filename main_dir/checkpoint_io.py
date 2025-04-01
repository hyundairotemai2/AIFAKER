"""
StarGAN v2 - CheckpointIO Module
Copyright (c) 2020-present NAVER Corp.
Licensed under CC BY-NC 4.0
"""

import os
import torch


class CheckpointIO:
    """모델 체크포인트 저장 및 로드를 관리하는 클래스"""
    
    def __init__(self, checkpoint_dir, checkpoint_prefix="checkpoint_{:06d}.pt", data_parallel=False):
        """
        CheckpointIO 초기화
        
        Args:
            checkpoint_dir (str): 체크포인트 파일이 저장될 디렉토리
            checkpoint_prefix (str): 체크포인트 파일 이름 템플릿 (기본값: "checkpoint_{:06d}.pt")
            data_parallel (bool): DataParallel 사용 여부
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_prefix = checkpoint_prefix
        self.data_parallel = data_parallel
        self.module_dict = {}
        
        # 체크포인트 디렉토리 생성
        os.makedirs(checkpoint_dir, exist_ok=True)
        print(f"[CheckpointIO] Initialized with directory: {checkpoint_dir}")

    def register_modules(self, **kwargs):
        """저장/로드할 모듈들을 등록
        
        Args:
            **kwargs: 이름과 모듈 쌍 (예: generator=gen_model)
        """
        self.module_dict.update(kwargs)
        print(f"[CheckpointIO] Registered modules: {list(kwargs.keys())}")

    def save(self, step):
        """현재 상태를 체크포인트로 저장
        
        Args:
            step (int): 현재 훈련 스텝
        """
        fname = os.path.join(self.checkpoint_dir, self.checkpoint_prefix.format(step))
        print(f"[CheckpointIO] Saving checkpoint to {fname}...")
        
        outdict = {}
        for name, module in self.module_dict.items():
            if self.data_parallel:
                outdict[name] = module.module.state_dict()
            else:
                outdict[name] = module.state_dict()
                
        torch.save(outdict, fname)
        print(f"[CheckpointIO] Checkpoint saved successfully")

    def load(self, step):
        """지정된 스텝의 체크포인트를 로드
        
        Args:
            step (int): 로드할 훈련 스텝
            
        Returns:
            dict: 로드된 모듈 상태 딕셔너리
        """
        fname = os.path.join(self.checkpoint_dir, self.checkpoint_prefix.format(step))
        assert os.path.exists(fname), f"[CheckpointIO] Checkpoint {fname} does not exist!"
        print(f"[CheckpointIO] Loading checkpoint from {fname}...")
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        module_dict = torch.load(fname, map_location=device)
        
        for name, module in self.module_dict.items():
            if self.data_parallel:
                module.module.load_state_dict(module_dict[name], strict=False)
            else:
                module.load_state_dict(module_dict[name], strict=False)
                
        print(f"[CheckpointIO] Checkpoint loaded successfully")
        return module_dict

    def get_latest_checkpoint(self):
        """디렉토리에서 가장 최근 체크포인트를 찾아 스텝 번호 반환
        
        Returns:
            int: 가장 최근 체크포인트의 스텝 번호, 없으면 None
        """
        checkpoint_files = [f for f in os.listdir(self.checkpoint_dir) 
                          if f.startswith(self.checkpoint_prefix.split('{')[0])]
        if not checkpoint_files:
            return None
            
        steps = [int(f.split('_')[-1].split('.')[0]) for f in checkpoint_files]
        return max(steps)


# 사용 예시
if __name__ == "__main__":
    # 더미 모델 생성
    class DummyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = torch.nn.Linear(10, 10)
    
    # 모델 인스턴스
    model1 = DummyModel()
    model2 = DummyModel()
    
    # CheckpointIO 인스턴스 생성
    checkpoint_io = CheckpointIO(
        checkpoint_dir="./checkpoints",
        checkpoint_prefix="model_checkpoint_{:06d}.pt",
        data_parallel=False
    )
    
    # 모듈 등록
    checkpoint_io.register_modules(generator=model1, discriminator=model2)
    
    # 체크포인트 저장
    checkpoint_io.save(step=1000)
    
    # 체크포인트 로드
    checkpoint_io.load(step=1000)
    
    # 가장 최근 체크포인트 확인
    latest_step = checkpoint_io.get_latest_checkpoint()
    print(f"Latest checkpoint step: {latest_step}")