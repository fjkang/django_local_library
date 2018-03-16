from django.shortcuts import render
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
import datetime

from .models import Book, Author, BookInstance, Genre
from .forms import RenewBookModelForm


# Create your views here.
def index(request):
    """
    View function for home page of site.
    """
    # 获取主函数需要用到的参数
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()
    # Available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()  # 注意!!status__exact是'__'不是'_'
    num_instances_onloan = BookInstance.objects.filter(status__exact='o').count()
    num_instances_reserved = BookInstance.objects.filter(status__exact='r').count()
    num_authors = Author.objects.count()  # The 'all()' is implied by default. all()默认可隐藏

    # 设置session,显示访问过的次数
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    # Render the HTML template index.html with the data in the context variable
    return render(
        request,
        'index.html',
        context={'num_books': num_books, 'num_instances': num_instances,
                 'num_instances_available': num_instances_available, 'num_authors': num_authors,
                 'num_instances_onloan': num_instances_onloan, 'num_instances_reserved': num_instances_reserved,
                 'num_visits': num_visits},
    )


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10


class BookDetailView(generic.DetailView):
    model = Book


class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10

class AuthorDetailView(generic.DetailView):
    model = Author


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """
    Generic class-based view listing books on loan to current user.
    """
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(borrower=self.request.user).filter(status__exact='o').order_by('due_back')


# challenge:添加图书管理员查看所有被借的图书
class LoanedBooksByAllListView(PermissionRequiredMixin, generic.ListView):
    """
    Generic class-based view listing books on loan to all user.
    """
    permission_required = 'catalog.staff_member_required'
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o').order_by('due_back')


@permission_required('catalog.can_mark_returned')
def renew_book_librarian(request, pk):
    """
    View function for renewing a specific BookInstance by librarian
    """
    book_inst = get_object_or_404(BookInstance, pk=pk)

    # 如果是"POST"请求
    if request.method == 'POST':
        # 创建一个表单实例,接收请求回来数据
        form = RenewBookModelForm(request.POST)

        # 检查数据是否有效
        if form.is_valid():
            # 把有效的数据传给需要更改的值(这里只传了due_back的值)
            book_inst.due_back = form.cleaned_data['due_back']
            book_inst.save()

            # 重定向到一个新的URL
            return HttpResponseRedirect(reverse('all-borrowed'))

    # 如果这是一个GET请求,生成一个缺省表单
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookModelForm(initial={'due_back': proposed_renewal_date, })

    return render(request, 'catalog/book_renew_librarian.html', {'form': form, 'bookinst': book_inst})


class AuthorCreate(CreateView):
    model = Author
    fields = '__all__'
    # initial = {'date_of_death': '2018-05-01', }


class AuthorUpdate(UpdateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']


class AuthorDelete(DeleteView):
    model = Author
    success_url = reverse_lazy('authors')


class BookCreate(CreateView):
    model = Book
    fields = '__all__'


class BookUpdate(UpdateView):
    model = Book
    fields = '__all__'


class BookDelete(DeleteView):
    model = Book
    success_url = reverse_lazy('books')
