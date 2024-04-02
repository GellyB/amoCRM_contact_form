import dotenv
import jwt
import requests
from datetime import datetime
import time
from random import randint
import logging
from requests.exceptions import JSONDecodeError
from dotenv import load_dotenv
import os

# Приём пути к каталогу текущего скрипта
script_dir = os.path.dirname(__file__)

# Формирование путь к файлу .env
dotenv_path = os.path.join(script_dir, 'test.env')

# Загрузка переменных окружения из файла .env
load_dotenv(dotenv_path)

# В эти четыре переменные записываются первые четыре значения из test.env
subdomain = os.getenv("AMOCRM_SUBDOMAIN")
client_id = os.getenv("AMOCRM_CLIENT_ID")
client_secret = os.getenv("AMOCRM_CLIENT_SECRET")
redirect_uri = os.getenv("AMOCRM_REDIRECT_URL")

# Секретный ключ интеграции. Может быть изменён
secret_code = "def502005cb021e4efe7135a546737a29fec2f2ef1cbbebd24aa7d201b1c209830695b39b35b05f739c33e3dc0bb4af3df4379078855dbec3d16c74bb3325a1a76f25c2ad0d91226f66fafd9f8ae8a7bb75929a9c82203f1e7b5753d6c3535ac37cdff5d355cd93f211128e4f0432c78da8437c82654a5712ee8ddfefb5f52751d76c71058daaed740b9122d0bfc44644e52b382a60c58cb2a0547a88d5679a98cf70d15ce261a3d44b6d4f10a73bff7a69ca244a29044f10491986d6acabac68ac3ca8f92f0dcf4bb466fd598604f5024428a0fff24aab8e96dc3f77e75246323d7068dd9370f905e08ea7bafcaba1e1ff12883f7e8bd8bcfa9a237f2417f2b0cb1fa7d4b7dc80540278a869a560ffdbebf9cf4cd8ab02196dad03babc32aaf3736461313401880d25d13db3312539158ae4860929535cbd19cc99080c8f0d2b26a18faad3dc10eb3211f64b9b5f1a94229f1468053bffadb43442763222b144deb38315bc5071d377486e5093be404c32ebc64a342906393825bfb9bf2499e8c55b2bdba367d12ec347726cc4723cdc1714d19bfc7df00d992474f8e8614135e23c3bef2ac4056df23e32bfef06b4e2e7de98b8c2e156c1e8711f39b48a7e930804159f780de960422101e207dd4fc065c364f3bad28c3a0a6069589b45d826d52724c"

# Функция проверки актуальности работы токена
def _is_expire(token: str):
    # Декодирование токена JWT без проверки подписи. 
    token_data = jwt.decode(token, options={"verify_signature": False})
    
    # Извление времи истечения токена из декодированных данных. 
    # Поскольку время истечения в формате Unix timestamp, 
    # используем datetime.utcfromtimestamp для преобразования в объект datetime
    exp = datetime.utcfromtimestamp(token_data["exp"])
    
    now = datetime.utcnow()

    # Провера на актуальность работы токена 
    return now >= exp


# Функция сохранения токенов
def _save_tokens(access_token: str, refresh_token: str):
    # Записываем в ключи test.env
    os.environ["AMOCRM_ACCESS_TOKEN"] = access_token
    os.environ["AMOCRM_REFRESH_TOKEN"] = refresh_token
    dotenv.set_key(dotenv_path, "AMOCRM_ACCESS_TOKEN", os.environ["AMOCRM_ACCESS_TOKEN"])
    dotenv.set_key(dotenv_path, "AMOCRM_REFRESH_TOKEN", os.environ["AMOCRM_REFRESH_TOKEN"])

# Фукнция приёма токена обновления (refresh_token)
def _get_refresh_token():
    return os.getenv("AMOCRM_REFRESH_TOKEN")

#  Фукнция приёма токена доступа (access_token)
def _get_access_token():
    return os.getenv("AMOCRM_ACCESS_TOKEN")

# Класс функций работы с API amoCRM. Все запросы будут отправлять JSON-объекты
class AmoCRMWrapper:
    def init_oauth2(self):
        
        # Добавление инициализированных ранее переменных в словарь
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": secret_code,
            "redirect_uri": redirect_uri
        }

        # Запрос за сервер. В {} используется субдомен
        response = requests.post("https://{}.amocrm.ru/oauth2/access_token".format(subdomain), json=data).json()
        
        # Получение ключей доступа из запроса
        access_token = response["access_token"]
        refresh_token = response["refresh_token"]

        # Запись ключей в test.env
        _save_tokens(access_token, refresh_token)
    
    def _base_request(self, **kwargs):
        
        # Проверка актуальности текущего токена доступа. 
        if _is_expire(_get_access_token()):
        
            # Приём нового в случае, если токен устарел.
            _get_new_tokens()


        access_token = "Bearer " + _get_access_token()

        headers = {"Authorization": access_token}
        
        # "type" сообщает, какой запрос нужно сделать: GET, GET с параметрами или POST
        req_type = kwargs.get("type")
        response = ""
        
        if req_type == "get":
            try:
                
                # kwargs.get("endpoint") - Приём конечной точки API или URL
                response = requests.get("https://{}.amocrm.ru{}".format(     
                    subdomain, kwargs.get("endpoint")), headers=headers).json()
            
            except JSONDecodeError as e:
                logging.exception(e)

        elif req_type == "get_param":
        
            url = "https://{}.amocrm.ru{}?{}".format(
                subdomain,
                kwargs.get("endpoint"), kwargs.get("parameters"))
            response = requests.get(str(url), headers=headers).json()
        
        elif req_type == "post":
        
            # json=kwargs.get("data") - Данные, которые будут отправляться на сервер, в формате JSON
            response = requests.post("https://{}.amocrm.ru{}".format(
                subdomain,                                
                kwargs.get("endpoint")), headers=headers, json=kwargs.get("data")).json()
        
        return response                

        _save_tokens(access_token, refresh_token)
                            
    def get_lead_by_id(self, lead_id):
        url = "/api/v4/leads/" + str(lead_id)
        return self._base_request(endpoint=url, type="get")
    
    def get_custom_field(self):
        return self._base_request(endpoint="api/v4/contacts/custom_fields", type="get")
    
    def add_contact(self, name, last_name, email, phone, field_code, field_id):
        
        url = "/api/v4/contacts"
        
        data = [
            {
                "first_name": name,
                "last_name": last_name,
                "responsible_user_id": 31660866,
                "created_by": 31660866,
                "custom_fields_values": [
                    {
                        "fielld_id": {{field_code}},
                        "values": [
                            {
                            "value": "test"
                            }
                        ]
                    },
                    {
                        "field_code": "PHONE",
                        "values":[
                            {
                                "enum_code": "WORK",
                                "value": {{phone}}
                            }
                        ]
                    },
                    {
                        "field_id": {{field_id}},
                        "values": [
                            {
                                "value": {{email}}
                            }
                        ]
                    }
                ]
            }
        ]
    
    
# Функция отправки запроса для получениия новой пары токенов
def _get_new_tokens():
    data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": _get_refresh_token(),
            "redirect_uri": redirect_uri
    }
    response = requests.post("https://{}.amocrm.ru/oauth2/access_token".format(subdomain), json=data).json()
    access_token = response["access_token"]
    refresh_token = response["refresh_token"]