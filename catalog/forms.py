from django.forms import ModelForm
from .models import BookInstance

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import datetime  # 用于检测日期区间


class RenewBookModelForm(ModelForm):
    # renewal_date = forms.DateField(help_text="Enter a date between now and 4 weeks(default 3).")

    def clean_due_back(self):  # <-django内置检测,格式为clean_<fieldname>()
        data = self.cleaned_data['due_back']

        # 检测日期是否为过去
        if data < datetime.date.today():
            raise ValidationError(_('Invalid date - renewal in past'))

        # 检测日期是否超过4周
        if data > datetime.date.today() + datetime.timedelta(weeks=4):
            raise ValidationError(_('Invalid date - renewal more than 4 weeks ahead'))

        # 记得一定要返回处理后的data
        return data

    class Meta:
        model = BookInstance
        fields = ['due_back', ]
        labels = {'due_back': _('Renew date'), }
        help_texts = {'due_back': _('Enter a date between now and 4 weeks (default 3).'), }
