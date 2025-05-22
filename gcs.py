import logging
import os
from datetime import timedelta
from multiprocessing import Pool

from google.cloud import storage
from tqdm import tqdm


class GCSClient:

    def __init__(self):
        self._client = storage.Client()

    def upload_directory_to_gcs(self, local_directory, bucket_name):
        directory_name = os.path.basename(os.path.normpath(local_directory))
        upload_args = []
        upload_blob_names = []

        for filename in os.listdir(local_directory):
            if not filename.startswith('.'):
                local_path = os.path.join(local_directory, filename)
                destination_blob_name = f"{directory_name}/{filename}"
                upload_blob_names.append(destination_blob_name)
                upload_args.append((local_path, bucket_name, destination_blob_name))

        for upload_arg in upload_args:
            self.upload_file(upload_arg)

        #with Pool(processes=4) as pool:
        #    results = list(tqdm(pool.imap(self.upload_file, upload_args), total=len(upload_args), desc="上传进度"))
        # logging.info(f"文件上传gcs结果：{results}")

        return upload_blob_names

    def upload_file(self, args):
        local_path, bucket_name, destination_blob_name = args
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_path, timeout=500)
        logging.info(f"文件 {os.path.basename(local_path)} 已上传")

    def list_gcs_blobs(self, bucket_name, folder_name, types):
        blobs = self._client.list_blobs(
            bucket_name, prefix=folder_name if folder_name.endswith('/') else folder_name + '/')
        return [blob.name for blob in blobs if blob.name[-4:] in types]

    @staticmethod
    def extract_gcs_path(gs_url):
        # gs://bucket/f/f => f/f
        return gs_url[5 + gs_url[5:].find('/') + 1:]

    @staticmethod
    def extract_bucket(url):
        if url.startswith("gs://"):
            parts = url[5:].split('/')
            return parts[0]
        return None

    def get_gcs_sign_url(self, bucket_name, blob_name, expiration_hours):
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        return (blob_name, blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET"
        ))


if __name__ == '__main__':
    assert GCSClient.extract_gcs_path("gs://bucket/1/2") == "1/2"

    DEFAULT_GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "online_highlight_dev")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "solar-router-391006-55ab81a8ae0e.json"

    sc = GCSClient()
    bs = sc.list_gcs_blobs(DEFAULT_GCS_BUCKET, "黑暗中的爱-(1-5)", [".mp4"])
    print([b.name for b in bs])
