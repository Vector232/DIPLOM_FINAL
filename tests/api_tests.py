import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()

@pytest.mark.django_db
def test_user_views(client):
    response_1 = client.post("/user/register", data={"first_name": "Ivan",
                                                    "last_name": "Ivanov",
                                                    "email": "ivanovivanshopmanager@mail.ru",
                                                    "password": "1234fwef123r1f1234",
                                                    "company": "Company I",
                                                    "position": "manager",
                                                    "type": "shop"
                                                    })
    
    response_2 = client.post("/user/register/confirm", data={"email": "ivanovivanshopmanager@mail.ru",
                                                               "token": response_1.data.get('token')})
    
    assert response_1.status_code == 200
    assert response_2.status_code == 200

    response_1 = client.post("/user/login", data={"email": "ivanovivanshopmanager@mail.ru",
                                                  "password": "1234fwef123r1f1234"})
    response_2 = client.post("/user/login", data={"email": "non_ivanovivanshopmanager@mail.ru",
                                                  "password": "1234fwef123r1f1234"})
    
    assert response_1.status_code == 200
    assert response_2.status_code == 403