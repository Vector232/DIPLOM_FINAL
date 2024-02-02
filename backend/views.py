from django.db import IntegrityError
from django.shortcuts import render
from django.db.models import Sum, Q, Prefetch
from django.core.mail import EmailMessage
from django.contrib.auth import authenticate
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from rest_framework import status, viewsets, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from distutils.util import strtobool
from requests import get
from ujson import loads as load_json
from yaml import load as load_yaml, Loader

from backend.models import User, Contact, Shop, Category, Product, ProductParameter, OrderItem, Order, ConfirmEmailToken, Parameter
from backend.serializers import UserSerializer, ContactSerializer, ShopSerializer, OrderSerializer
from backend.serializers import  ProductSerializer, CategorySerializer, OrderItemAddSerializer

class PartnerUpdate(APIView):
    permission_classes = [IsAuthenticated]
    
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
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                Product.objects.filter(shop=shop.id).delete()
                for item in data['goods']:
                    category = Category.objects.get(id=item['category'])
                    product, _ = Product.objects.get_or_create(name=item['name'], 
                                                               category=Category.objects.get(id=item['category']), 
                                                               external_id=item['id'],
                                                               model=item['model'],
                                                               quantity=item['quantity'],
                                                               price=item['price'],
                                                               price_rrc=item['price_rrc'],
                                                               shop=Shop.objects.get(id=shop.id) )
                    for name, value in item['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product=product,
                                                        parameter=parameter,
                                                        value=value)
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
                    return Response({'status': True, 'token': token.key, 'data': request.data})
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
                return Response({'Status': False, 'ERROR': 'Неправильно указан token или email!'})
        return Response({'Status': False, 'ERROR': 'Не все аргументы указыны!'}) 

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
                    {'status': False, 'ERROR': 'Не все арументы указаны!'})

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

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
    
class DetailUser(APIView):
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
                    {'status': False, 'ERROR': 'Не все арументы указаны!'})

class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        if {'id'}.issubset(request.data):
            try:
                contact = Contact.objects.get(pk=int(request.data['id']))
            except ValueError:
                return Response({'status': False, 'ERROR': 'Не верный тип поля <ID>!'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = ContactSerializer(contact, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'status': True}, status=status.HTTP_200_OK)
            return Response({'status': False, 'ERROR': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': False, 'ERROR': 'Не все необходимые поля указаны!'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        if {'items'}.issubset(request.data):
            for item in request.data["items"].split(','):
                try:
                    contact = Contact.objects.get(pk=int(item))
                    contact.delete()
                except ValueError:
                    return Response({'status': False, 'ERROR': 'Не верный тип поля!'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status': True}, status=status.HTTP_204_NO_CONTENT)
        return Response({'status': False, 'ERROR': 'ID контактов не указаны!'}, status=status.HTTP_400_BAD_REQUEST)
    
class PartnerState(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'ERROR': 'Только для магазинов!'}, status=status.HTTP_403_FORBIDDEN)
        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'ERROR': 'Только для магазинов!'}, status=status.HTTP_403_FORBIDDEN)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return Response({'status': True})
            except ValueError as error:
                return Response({'status': False, 'ERROR': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': False, 'ERROR': 'Не указано поле <Статус>!'}, status=status.HTTP_400_BAD_REQUEST)

class PartnerOrders(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return Response({'status': False, 'ERROR': 'Только для магазинов!'}, status=status.HTTP_403_FORBIDDEN)
        prefetch = Prefetch('ordered_items', queryset=OrderItem.objects.filter(
            shop__user_id=request.user.id))
        order = Order.objects.filter(
            ordered_items__shop__user_id=request.user.id).exclude(status='cart')\
            .prefetch_related(prefetch).select_related('contact').annotate(
                    total_sum=Sum('ordered_items__total_amount'),
                    total_quantity=Sum('ordered_items__quantity'))
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

class ShopView(generics.ListAPIView):
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer

class CategoryView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ApiListPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ProductView(APIView):
    pagination_class = ApiListPagination

    def get(self, request, *args, **kwargs):
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')
        if shop_id:
            query = query & Q(shop_id=shop_id)
        if category_id:
            query = query & Q(category_id=category_id)
        queryset = Product.objects.filter(query).select_related('shop', 'category').\
            prefetch_related('product_parameters').distinct()
        serializer = ProductSerializer(queryset, many=True)
        return Response(serializer.data)

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CartView(APIView):
    """Корзина покупателя"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cart = Order.objects.filter(
            user_id=request.user.id, status='cart'
        ).prefetch_related('ordered_items').annotate(
            total_sum=Sum('ordered_items__total_amount'),
            total_quantity=Sum('ordered_items__quantity')
        )
        serializer = OrderSerializer(cart, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        items = request.data.get('items')
        if items:
            try:
                items_dict = load_json(items)
            except ValueError:
                Response({'Status': False, 'ERROR': 'Неверный формат запроса!'})
            else:
                cart, _ = Order.objects.get_or_create(user_id=request.user.id, status='cart')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': cart.id})
                    product = Product.objects.filter(external_id=order_item['external_id']).values('category', 'shop', 'name', 'price')
                    order_item.update({'category': product[0]['category'], 'shop': product[0]['shop'], 'product_name': product[0]['name'], 'price': product[0]['price']})
                    serializer = OrderItemAddSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return Response({'status': False, 'ERROR': str(error)}, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            objects_created += 1
                    else:
                        return Response({'status': False, 'ERROR': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'status': True, 'num_objects': objects_created})

        return Response({'status': False, 'ERROR': 'Не все необходимые поля указаны!'},
                        status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        items = request.data.get('items')
        if items:
            try:
                items_dictionary = load_json(items)
            except ValueError:
                Response({'Status': False, 'ERROR': 'Неверный формат запроса!'})
            else:
                cart, _ = Order.objects.get_or_create(user_id=request.user.id, status='cart')
                objects_updated = 0
                for item in items_dictionary:
                    if isinstance(item['id'], int) and isinstance(item['quantity'], int):
                        objects_updated += OrderItem.objects.filter(order_id=cart.id, id=item['id']).update(quantity=item['quantity'])
                return Response({'status': True, 'edit_objects': objects_updated})
        return Response({'status': False, 'ERROR': 'Не все поля указаны!'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        items = request.data.get('items')
        if items:
            items_list = items.split(',')
            cart, _ = Order.objects.get_or_create(user_id=request.user.id, status='cart')
            query = Q()
            objects_deleted = False
            for item_id in items_list:
                if item_id.isdigit():
                    query = query | Q(order_id=cart.id, id=item_id)
                    objects_deleted = True
            if objects_deleted:
                count = OrderItem.objects.filter(query).delete()[0]
                return Response({'status': True, 'del_objects': count}, status=status.HTTP_204_NO_CONTENT)
        return Response({'status': False, 'ERROR': 'Не все поля указаны!'}, status=status.HTTP_400_BAD_REQUEST)

class OrderView(APIView):
    """Заказы"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        order = Order.objects.filter(
            user_id=request.user.id).annotate(total_quantity=Sum('ordered_items__quantity'), total_sum=Sum(
                'ordered_items__total_amount')).distinct()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'Status': False, 'ERROR': 'Authorization required!'}, status=403)
        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                            contact_id=request.data['contact'], status='new')
                except IntegrityError as error:
                    print(error)
                    return Response({'Status': False, 'ERROR': 'Аргументы указаны неправильно!'})
                else:
                    if is_updated:
                        return Response({'Status': True})
                    else:
                        error_message = 'ERROR'         
        return Response({'Status': False, 'ERROR': 'Не все необходимые аргументы указаны!'})