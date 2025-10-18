import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

os.environ["TESTING"] = "True"

# Импортируем приложение и модели из основного файла
from main import app, get_db, Base, PersonDB, engine

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Переопределяем зависимость базы данных для тестов
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Фикстура для клиента тестирования
@pytest.fixture
def client():
    # Создаем таблицы перед тестом
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Удаляем таблицы после теста
    Base.metadata.drop_all(bind=engine)

# Тестовые данные
TEST_PERSON_DATA = {
    "name": "John Doe",
    "age": 30,
    "address": "123",
    "work": "123"
}

TEST_PERSON_UPDATE_DATA = {
    "name": "Jane Smith",
    "age": 25,
    "address": "456",
    "work": "456"
}

class TestPersonsAPI:
    def test_create_person_success(self, client):
        """Тест успешного создания человека"""
        response = client.post("/persons", json=TEST_PERSON_DATA)
        
        assert response.status_code == 201
        assert response.headers["Location"] == "/persons/1"

    def test_get_person_success(self, client):
        """Тест успешного получения информации о человеке"""
        # Сначала создаем человека
        client.post("/persons", json=TEST_PERSON_DATA)
        
        # Затем получаем его
        response = client.get("/persons/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "John Doe"
        assert data["age"] == 30

    def test_get_person_not_found(self, client):
        """Тест получения несуществующего человека"""
        response = client.get("/persons/999")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"

    def test_get_all_persons(self, client):
        """Тест получения списка всех людей"""
        # Создаем несколько человек
        client.post("/persons", json=TEST_PERSON_DATA)
        client.post("/persons", json=TEST_PERSON_UPDATE_DATA)
        
        response = client.get("/persons")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "John Doe"
        assert data[1]["name"] == "Jane Smith"

    def test_update_person_success(self, client):
        """Тест успешного обновления информации о человеке"""
        # Сначала создаем человека
        client.post("/persons", json=TEST_PERSON_DATA)
        
        # Затем обновляем его
        response = client.patch("/persons/1", json=TEST_PERSON_UPDATE_DATA)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Jane Smith"
        assert data["age"] == 25

    def test_update_person_not_found(self, client):
        """Тест обновления несуществующего человека"""
        response = client.patch("/persons/999", json=TEST_PERSON_UPDATE_DATA)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"

    def test_delete_person_success(self, client):
        """Тест успешного удаления человека"""
        # Сначала создаем человека
        client.post("/persons", json=TEST_PERSON_DATA)
        
        # Затем удаляем его
        response = client.delete("/persons/1")
        
        assert response.status_code == 204
        
        # Проверяем, что человека больше нет
        get_response = client.get("/persons/1")
        assert get_response.status_code == 404

    def test_delete_person_not_found(self, client):
        """Тест удаления несуществующего человека"""
        response = client.delete("/persons/999")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"

    def test_create_and_retrieve_person_flow(self, client):
        """Комплексный тест: создание и последующее получение человека"""
        # Создаем человека
        create_response = client.post("/persons", json=TEST_PERSON_DATA)
        assert create_response.status_code == 201
        
        location = create_response.headers["Location"]
        person_id = location.split("/")[-1]
        
        # Получаем созданного человека по Location header
        get_response = client.get(location)
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["id"] == int(person_id)
        assert data["name"] == "John Doe"
        assert data["age"] == 30

# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v"])