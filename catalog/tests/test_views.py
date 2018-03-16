from django.test import TestCase

# 测试分页功能的导入
from catalog.models import Author
from django.urls import reverse
# 测试用户借书功能的导入
import datetime
from django.utils import timezone

from catalog.models import BookInstance, Book, Genre, Language
from django.contrib.auth.models import User  # 用来设置一个借书用户

# 更新借书日期功能的导入
from django.contrib.auth.models import Permission


# 第一个类
class AuthorListViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # 创建13个作者来测试分页
        number_of_authors = 13
        for author_num in range(number_of_authors):
            Author.objects.create(first_name='Christina {}'.format(author_num),
                                  last_name='Surname {}'.format(author_num), )

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/catalog/authors/')
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)

        self.assertTemplateUsed(resp, 'catalog/author_list.html')

    def test_pagination_is_ten(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] == True)
        self.assertTrue(len(resp.context['author_list']) == 10)

    def test_lists_all_authors(self):
        # 转到第二页并确认还有3个作者显示
        resp = self.client.get(reverse('authors') + '?page=2')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] == True)
        self.assertTrue(len(resp.context['author_list']) == 3)


# 第二个类
class LonaedBookInstancesByUserListViewTest(TestCase):

    def setUp(self):
        # 创建2个用户
        test_user1 = User.objects.create_user(username='testuser1', password='123456')
        test_user1.save()
        test_user2 = User.objects.create_user(username='testuser2', password='123456')
        test_user2.save()

        # 创建一本书
        test_author = Author.objects.create(first_name='John', last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(language='English')
        test_book = Book.objects.create(
            title='Book Title', summary='My book summary',
            isbn='ABCDEFG', author=test_author, language=test_language)
        # 创建一个种类作为POST
        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)  # 不允许多对多关系
        test_book.save()

        # 创建30本书的副本实例
        number_of_book_copies = 30
        for book_copy in range(number_of_book_copies):
            return_date = timezone.now() + datetime.timedelta(days=book_copy % 5)
            if book_copy % 2:
                the_borrower = test_user1
            else:
                the_borrower = test_user2
            status = 'm'
            BookInstance.objects.create(
                book=test_book, imprint='Unlikely Imprint, 2016',
                due_back=return_date, borrower=the_borrower, status=status)

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(resp, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        login = self.client.login(username='testuser1', password='123456')
        resp = self.client.get(reverse('my-borrowed'))

        # 检查用户是否登陆
        self.assertEqual(str(resp.context['user']), 'testuser1')
        # 检查服务器响应是否为成功状态
        self.assertEqual(resp.status_code, 200)

        # 检查模板是否正确
        self.assertTemplateUsed(resp, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_book_in_list(self):
        login = self.client.login(username='testuser1', password='123456')
        resp = self.client.get(reverse('my-borrowed'))

        # 测试登陆是否成功
        self.assertEqual(str(resp.context['user']), 'testuser1')
        # 测试服务器成功响应
        self.assertEqual(resp.status_code, 200)

        # 检测初始化时当前用户没有借书
        self.assertTrue('bookinstance_list' in resp.context)
        self.assertEqual(len(resp.context['bookinstance_list']), 0)

        # 改变所有测试的书状态为o
        get_ten_books = BookInstance.objects.all()[:10]
        for copy in get_ten_books:
            copy.status = 'o'
            copy.save()

        # 检查列表是否有书可借
        resp = self.client.get(reverse('my-borrowed'))
        # 测试登陆是否成功
        self.assertEqual(str(resp.context['user']), 'testuser1')
        # 测试服务器成功响应
        self.assertEqual(resp.status_code, 200)

        self.assertTrue('bookinstance_list' in resp.context)

        # 确认所有书都是testuser1借的
        for bookitem in resp.context['bookinstance_list']:
            self.assertEqual(resp.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):

        # 改变所有的书状态为'o'
        for copy in BookInstance.objects.all():
            copy.status = 'o'
            copy.save()

        login = self.client.login(username='testuser1', password='123456')
        resp = self.client.get(reverse('my-borrowed'))

        # 测试登陆是否成功
        self.assertEqual(str(resp.context['user']), 'testuser1')
        # 测试服务器成功响应
        self.assertEqual(resp.status_code, 200)

        # 确认以10本书分页
        self.assertEqual(len(resp.context['bookinstance_list']), 10)

        last_date = 0
        for copy in resp.context['bookinstance_list']:
            if last_date == 0:
                last_date = copy.due_back
            else:
                self.assertTrue(last_date <= copy.due_back)


# 第三个类
class RenewBookInstanceViewTest(TestCase):

    def setUp(self):
        # 创建2个用户
        test_user1 = User.objects.create_user(username='testuser1', password='123456')
        test_user1.save()
        test_user2 = User.objects.create_user(username='testuser2', password='123456')
        test_user2.save()
        # 对user2增加还书的权限
        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

        # 创建一本书
        test_author = Author.objects.create(first_name='John', last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(language='English')
        test_book = Book.objects.create(
            title='Book Title', summary='My book summary',
            isbn='ABCDEFG', author=test_author, language=test_language)
        # 创建一个种类作为POST
        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)  # 不允许多对多关系
        test_book.save()

        # user1借一个书本
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
            book=test_book, imprint='Unlikely Imprint, 2016',
            due_back=return_date, borrower=test_user1, status='o')

        # user2借一个书本
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance2 = BookInstance.objects.create(
            book=test_book, imprint='Unlikely Imprint, 2016',
            due_back=return_date, borrower=test_user2, status='o')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }))
        # 要手动检测重定向(不能用asserRedirect,因为那个url是不可预测的)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_redirect_if_logged_in_but_not_correct_permission(self):
        login = self.client.login(username='testuser1', password='123456')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }))

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_logged_in_with_permission_borrowed_book(self):
        login = self.client.login(username='testuser2', password='123456')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance2.pk, }))

        # 用有权限的user2测试
        self.assertEqual(resp.status_code, 200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        login = self.client.login(username='testuser2', password='123456')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }))

        # 用有权限的user2测试所有书本
        self.assertEqual(resp.status_code, 200)

    def test_Http404_for_invalid_book_if_logged_in(self):
        import uuid
        test_uid = uuid.uuid4()  # UID肯定不会跟书本实例匹配
        login = self.client.login(username='testuser2', password='123456')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': test_uid, }))
        self.assertEqual(resp.status_code, 404)

    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='123456')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }))
        self.assertEqual(resp.status_code, 200)

        # 检测使用的模板是否正确
        self.assertTemplateUsed(resp, 'catalog/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        login = self.client.login(username='testuser2', password='123456')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }))
        self.assertEqual(resp.status_code, 200)

        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(resp.context['form'].initial['due_back'], date_3_weeks_in_future)

    def test_redirects_to_all_borrowed_book_list_on_success(self):
        login = self.client.login(username='testuser2', password='123456')
        valid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=2)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }),
                                {'due_back': valid_date_in_future}
                                )

        self.assertRedirects(resp, reverse('all-borrowed'), fetch_redirect_response=False)
        # 这里要加上fetch_redirect_response=False 或者target_status_code=302 不然会测试失败,报错为:
        # AssertionError: 302 != 200 :
        # Couldn't retrieve redirection page '/catalog/allbooks/': response code was 302 (expected 200)

    def test_form_invalid_renewal_date_past(self):
        login = self.client.login(username='testuser2', password='123456')
        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }),
                                {'due_back': date_in_past}
                                )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'due_back', 'Invalid date - renewal in past')

    def test_form_invalid_renewal_date_future(self):
        login = self.client.login(username='testuser2', password='123456')
        invalid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=5)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk, }),
                                {'due_back': invalid_date_in_future}
                                )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'due_back', 'Invalid date - renewal more than 4 weeks ahead')