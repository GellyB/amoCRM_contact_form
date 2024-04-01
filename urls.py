import dotenv
import jwt
import requests
from datetime import datetime
import time
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
secret_code = "def50200f15aa5272afef3f89a212a6038e901e11ec63a5f28a443b17c6ac15a975053b9907f614402782fe0112faaef520889be634d57f7b4561c4fa3293768b2c3e9d9c694ae4b1e2c7d34f95cb5c48c2c0c3be5a313a7f7cd33297ae2283cd76b4516168722ffa2514a25d544d5be8b1d37c8739db6b9f6d070206acb2f252573b4be037e4daa52d563618efc3d1eddeca6ffa50600d5da910e377434a9807948bae890c250d7218381b17f5d1e667ab5fc29ca4c296ef246e023c9e0945f8a06505993e4f8ae94e1a7915200855ef88635f9a97e4ef3dfe484e0272d23b0e1f279ef7a9b19a66dd1e7958ea251d1267be4176834b3af4033113fde305f5a734ee4f18bb21a574f7a72e48aeaf026c7ae54c3454a0fa8467df999ed65e98b200d0553778731baccfc0e7e2324eb84982d18e28c7bfbb1e1787d7e079c572cec8a468c2ca185a7efa5091dca714e38cde76948d606ce7ae199bc5216dd4f7f0e8e3f38bb10989c01b518bb703f61fbd83b40ca7fa99ada0c1a31432abf9316359ac917e1c639e5bdccd6f816ef969d95469e229885ea50286a604fe82748952bb3174bbfa4f34e4264a1f48234477f05aebef0d69ca50f2eaa12016223319d50cbca4ef0586cce70e8f1afa913d58eefcc36e3000ba3e37c470061f388fffc312fba75"

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

    _save_tokens(access_token, refresh_token)
                        
