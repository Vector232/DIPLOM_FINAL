from django.db import models


STATUS_CHOICES = (
    ('cart', 'Корзина'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)


# Нужно плотно разобраться с Джанговскими способами реализации авторизации и т.д.  !!!!!!!!!!!!
class User(models.Model): # временное решение
	name = models.CharField(max_length=50, verbose_name='Имя')

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
