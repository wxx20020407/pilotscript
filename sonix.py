import json
from typing import List

import requests


class SonixClient:
    DEFAULT_BASEURL = "https://api.sonix.ai/v1"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def new_folder(self, folder):
        response = requests.post(
            f"{self.DEFAULT_BASEURL}/folders",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"name": folder}
        )

        return response.json()

    def list_folders(self):
        return requests.get(
            f"{self.DEFAULT_BASEURL}/folders",
            headers={"Authorization": f"Bearer {self._api_key}"}
        ).json()

    def get_folder(self, folder):
        folders = self.list_folders().get("folders")
        if folders is not None and len(folders) > 0:
            for f in folders:
                if f.get("name") == folder:
                    return f
        return None

    def upload_media(self, folder_id: str, file_info: tuple[str, str], language: str = 'en'):
        return requests.post(
            f"{self.DEFAULT_BASEURL}/media",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "name": file_info[0],
                "file_url": file_info[1],
                "language": language,
                "folder_id": folder_id
            }
        ).json()

    def get_media_status(self, media_id: str):
        return requests.get(
            f"{self.DEFAULT_BASEURL}/media/{media_id}",
            headers={"Authorization": f"Bearer {self._api_key}"}
        ).json()

    def batch_upload_medias(self, folder_id: str, files_info: List[tuple[str, str]], language: str = 'en'):
        return [self.upload_media(folder_id, file_info, language) for file_info in files_info]

    def list_media(self, page_num: int = 1, search: str = ""):
        return requests.get(
            f"{self.DEFAULT_BASEURL}/media?page={page_num}&search={search}",
            headers={"Authorization": f"Bearer {self._api_key}"}
        ).json()

    def get_text_transcript(self, media_id):
        response = requests.get(
            f"{self.DEFAULT_BASEURL}/media/{media_id}/transcript",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=60
        )
        response.encoding = 'utf-8'

        return response.text


if __name__ == '__main__':
    client = SonixClient(api_key="HwD0K6mdKV1xOpvlQtrUIQtt")
    # print(client.new_folder("test"))
    # print(client.list_folders())
    # print(client.get_folder("test"))
    # fid = client.get_folder("test").get("id")
    # print(json.dumps(client.list_media(search="黑暗中的爱"), indent=4, ensure_ascii=False))
    print(client.get_text_transcript("xy99rNVx"))
