""" Временный фал для того, чтобы по шагам с отладкой переработать 
    иеющийся код и довести его до рабочего состояния. """

from environs import Env

env = Env()  # Создаем экземпляр класса Env
env.read_env()  # Методом read_env() читаем файл .env и загружаем из него переменные в окружение

DATABASE_URL=f"postgresql+asyncpg://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}@{env('POSTGRES_HOST')}:5432/{env('POSTGRES_DB')}"
