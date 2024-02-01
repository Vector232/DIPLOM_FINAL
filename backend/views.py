from django.shortcuts import render
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from requests import get
from yaml import load as load_yaml, Loader

from backend.models import User, Contact, Shop, Category, Product, ProductParameter, OrderItem, Order, ConfirmEmailToken
from backend.serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class PartnerUpdate(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'change_price'

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'ERROR': 'Только для магазинов!'}, status=status.HTTP_403_FORBIDDEN)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return Response({'status': False, 'ERROR': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(user_id=request.user.id, defaults={'name': data['shop'], 'url': url})
                if shop.name != data['shop']:
                    return Response({'status': False, 'ERROR': 'Некорректное навание магазина в передаваемом файле!'}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'status': True})
            
        return Response({'status': False, 'ERROR': 'Не все необходимые поля указаны!'}, status=status.HTTP_400_BAD_REQUEST)
    
def on_change_order_status(user_id, order_id):
    """Письмо о статусе заказа"""
    user = User.objects.get(id=user_id)
    order = Order.objects.get(id=order_id)
    to_email = user.email
    message = f'Заказ номер { order_id} имеет статус "{order.status.upper()}"!'
    mail_subject = 'Статус изменен!'
    email = EmailMessage(mail_subject, message, to=[to_email])
    email.send()

class RegisterUser(APIView):
    """Регистрация покупателя"""
    throttle_scope = 'register'
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as error:
                return Response({'status': False, 'ERROR': {'password': error}}, status=status.HTTP_403_FORBIDDEN)
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
                    return Response({'status': True, 'token': token.key})
                else:
                    return Response({'status': False, 'ERROR': user_serializer.errors}, status=status.HTTP_403_FORBIDDEN
                                    )

        return Response({'status': False, 'ERROR': 'Не все поля указаны!'}, status=status.HTTP_400_BAD_REQUEST)

class Сonfirmation(APIView):
    """Подтверждение регистрации""" 
    def post(self, request, *args, **kwargs):
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return Response({
                    'Status': True
                })
            else:
                return Response({'Status': False, 'ERRORS': 'Неправильно указан token или email!'})
        return Response({'Status': False, 'ERRORS': 'Не все аргументы указыны!'}) 

class LoginUser(APIView):
    """Авторизация"""
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response({'status': True, 'token': token.key})
            return Response({'status': False, 'ERROR': 'Ошибка входа!'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': False, 'ERROR': 'Не все поля указаны!'}, status=status.HTTP_400_BAD_REQUEST)

class UserInfo(APIView):
    """Просмотр и изменение данных пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {'password'}.issubset(request.data):
            if 'password' in request.data:
                try:
                    validate_password(request.data['password'])
                except Exception as error:
                    return Response({'status': False, 'ERROR': {'password': error}}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    request.user.set_password(request.data['password'])
            user_serializer = UserSerializer(request.user, data=request.data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'status': False, 'ERRORS': 'Не все арументы указаны!'})
