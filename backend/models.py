from django.db import models

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser

from django_rest_passwordreset.tokens import get_token_generator

STATUS_CHOICES = (
    ('cart', 'Корзина'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

USER_TYPE = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not password:
            raise ValueError('Необходимо задать пароль!')
        if not email:
            raise ValueError('Необходимо указать Email!')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    username = None
    email = models.EmailField(verbose_name='Email', unique=True)
    company = models.CharField(verbose_name='Компания', max_length=50, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=50, blank=True)
    is_active = models.BooleanField(('active'), default=False)
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE, max_length=5, default='buyer')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class Contact(models.Model):
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts', blank=True, on_delete=models.CASCADE)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=50, verbose_name='Улица')
    house = models.CharField(max_length=50, verbose_name='Дом', blank=True)
    structure = models.CharField(max_length=50, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=50, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=50, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=50, verbose_name='Телефон')

    def __str__(self):
        return f'{self.city}, ул.{self.street}, дом {self.house} ({self.phone})'	

class ConfirmEmailToken(models.Model):
    user = models.ForeignKey(User, related_name='confirm_email_tokens', on_delete=models.CASCADE,
		verbose_name="Связанный пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата выдачи токена.")
    key = models.CharField(verbose_name="Ключ", max_length=100, db_index=True, unique=True)

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return f"Токен подтверждения Email для пользователя {self.user}"

class Shop(models.Model):
	name = models.CharField(max_length=50, verbose_name='Название')
	url = models.URLField(verbose_name='Ссылка на файл прайса', null=True, blank=True)
	user = models.OneToOneField(User, verbose_name='Пользователь', blank=True, null=True, on_delete=models.CASCADE)
	state = models.BooleanField(verbose_name='Cтатус получения заказов', default=True)

	def __str__(self):
		return self.name

class Category(models.Model):
	name = models.CharField(max_length=50, verbose_name='Название')
	shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

	def __str__(self):
		return self.name


class Product(models.Model):
	name = models.CharField(max_length=50, verbose_name='Название')
	category = models.ForeignKey(Category, verbose_name='Категория', related_name='products', blank=True, on_delete=models.CASCADE)
	model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
	external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
	shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='products_info', blank=True, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(verbose_name='Количество')
	price = models.PositiveIntegerField(verbose_name='Цена')
	price_rrc = models.PositiveIntegerField(verbose_name='Рекомендуемая розничная цена')

	def __str__(self):
		return self.name

class Parameter(models.Model):
	name = models.CharField(max_length=50, verbose_name='Название')

	def __str__(self):
		return self.name

class ProductParameter(models.Model):
	product = models.ForeignKey(Product, verbose_name='Информация о продукте', related_name='product_parameters', blank=True, on_delete=models.CASCADE)
	parameter = models.ForeignKey(Parameter, verbose_name='Параметр',  related_name='parameter', blank=True, on_delete=models.CASCADE)
	value = models.CharField(verbose_name='Значение', max_length=100)

	def __str__(self):
		return f'{self.product} - {self.parameter} {self.value}'

class Order(models.Model):
	user = models.ForeignKey(User, verbose_name='Пользователь', related_name='shopAPI', blank=True, on_delete=models.CASCADE)
	status = models.CharField(verbose_name='Статус', choices=STATUS_CHOICES, max_length=50, default='cart')
	contact = models.ForeignKey(Contact, verbose_name='Контакт', blank=True, null=True, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	def __str__(self):
		return str(self.created)

class OrderItem(models.Model):
	order = models.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items', blank=True, on_delete=models.CASCADE)
	category = models.ForeignKey(Category, verbose_name='Категория товара', blank=True, null=True, on_delete=models.SET_NULL)
	shop = models.ForeignKey(Shop, verbose_name='магазин', blank=True, null=True, on_delete=models.SET_NULL)
	product_name = models.CharField(max_length=50, verbose_name='Название товара')
	external_id = models.PositiveIntegerField(verbose_name='Внешний ИД')
	quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
	price = models.PositiveIntegerField(default=0, verbose_name='Цена')
	total_amount = models.PositiveIntegerField(default=0, verbose_name='Общая стоимость')

	def __str__(self):
		return self.product_name

	def save(self, *args, **kwargs):
		self.total_amount = self.price * self.quantity
		super(OrderItem, self).save(*args, **kwargs)
