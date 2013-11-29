from django.forms import Form
from django.forms import MultipleChoiceField, ChoiceField

class TagSearchForm(Form):
    selectedTags = MultipleChoiceField()

    def __init__(self, tags, conn=None, *args, **kwargs):
        super(TagSearchForm, self).__init__(*args, **kwargs)

        # Process Tags into choices (lists of tuples)
        self.fields['selectedTags'].choices = tags
        self.conn = conn