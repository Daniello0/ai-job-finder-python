"""User-facing text messages for chat and backend client."""

INITIAL_ASSISTANT_MESSAGE = (
    "Опишите ваш опыт, стек и ожидания — я подберу вакансию и покажу ключевые детали."
)
CHAT_INPUT_PLACEHOLDER = "Например: Junior Python, FastAPI, удаленно в Минске"
ASSISTANT_RUNNING_MESSAGE = "Running..."

SUMMARY_SUCCESS = "Нашел наиболее релевантные вакансии под ваш запрос."
SUMMARY_EMPTY_RESULTS = (
    "По текущему запросу подходящие вакансии не найдены. "
    "Уточните стек или добавьте больше деталей про опыт."
)
SUMMARY_NETWORK_FAILURE = "Не удалось связаться с backend API"

ERROR_UNKNOWN_BACKEND = "Backend returned an unknown error."
ERROR_ENDPOINT_NOT_FOUND = "Endpoint /api/v1/search не найден (404). Проверьте backend."
ERROR_BACKEND_UNAVAILABLE_TEMPLATE = (
    "Backend временно недоступен ({status_code}). {details}"
)
ERROR_BACKEND_REQUEST_TEMPLATE = "Ошибка запроса к backend ({status_code}). {details}"

DETAILS_PREFIX = " Details: "
