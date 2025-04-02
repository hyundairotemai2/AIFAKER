# celery_worker.py
from celery import Celery
import os
from dotenv import load_dotenv
from PGD_noise import PGDModelDummyGenerator, PGDModelDummyStyleEncoder, PGDModelDummyLPIPS, pgdmodel_attack_on_image
import torch
from PIL import Image
import io
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.cosmos import CosmosClient
import uuid
import base64

load_dotenv()

app = Celery("tasks", broker="redis://localhost:6379/0")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PGD_NETS = {
    "generator": PGDModelDummyGenerator().to(device),
    "style_encoder": PGDModelDummyStyleEncoder(out_dim=64).to(device),
}
PGD_LPIPS_MODEL = PGDModelDummyLPIPS()
PGD_Y_REF = torch.zeros(1, 3, 256, 256).to(device)

# Azure 설정
BLOB_CONNECTION_STRING = os.getenv('BLOB_CONNECTION_STRING')
BLOB_CONTAINER_NAME = "blog-images"
STORAGE_ACCOUNT_NAME = os.getenv('STORAGE_ACCOUNT_NAME')
STORAGE_ACCOUNT_KEY = os.getenv('STORAGE_ACCOUNT_KEY')

COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
COSMOS_DATABASE_NAME = os.getenv('COSMOS_DATABASE_NAME')
COSMOS_POSTS_CONTAINER = "posts"

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
cosmos_database = cosmos_client.get_database_client(COSMOS_DATABASE_NAME)
cosmos_container = cosmos_database.get_container_client(COSMOS_POSTS_CONTAINER)

def generate_unique_id():
    return str(uuid.uuid4())

def upload_to_blob(file_data, filename, user_id, post_id):
    filename = f"{user_id}/{post_id}/{filename}"
    blob_client = blob_container_client.get_blob_client(filename)
    blob_client.upload_blob(file_data, overwrite=True)

    sas_token = generate_blob_sas(
        account_name=STORAGE_ACCOUNT_NAME,
        container_name=blob_container_client.container_name,
        blob_name=filename,
        account_key=STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=24)
    )

    return f"{blob_client.url}?{sas_token}"

@app.task
def apply_pgd_filter_task(image_bytes_base64, filename, post_id, user_id):
    try:
        image_data = base64.b64decode(image_bytes_base64)
        temp_filename = f"temp_{generate_unique_id()}.png"
        with open(temp_filename, "wb") as f:
            f.write(image_data)

        result_img = pgdmodel_attack_on_image(
            image_path=temp_filename,
            nets=PGD_NETS,
            lpips_model=PGD_LPIPS_MODEL,
            y_ref=PGD_Y_REF,
            epsilon=0.05,
            alpha=0.01,
            num_iter=5,
        )

        os.remove(temp_filename)
        buffered = io.BytesIO()
        result_img.save(buffered, format="PNG")
        filtered_image_data = buffered.getvalue()

        filtered_filename = f"pgd_filtered_{filename}"
        filtered_image_url = upload_to_blob(filtered_image_data, filtered_filename, user_id, post_id)

        # Cosmos DB 업데이트
        query = f"SELECT * FROM c WHERE c.id = '{post_id}'"
        posts = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
        if posts:
            post = posts[0]
            post['filter_applied'] = True
            post['filtered_image_url'] = filtered_image_url
            post['image_url'] = filtered_image_url
            cosmos_container.replace_item(item=post, body=post)

    except Exception as e:
        print(f"[Celery Task Error] {e}")
