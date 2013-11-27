from django.forms import Form
from django.forms import MultipleChoiceField, ChoiceField

class TagSearchForm(Form):
    # Tags which are already part of the search
    selectedTags = ChoiceField()
    # Tags which could potentially be a part of the search
    availableTags = ChoiceField()


    def __init__(self, tags, conn=None, *args, **kwargs):
        super(TagSearchForm, self).__init__(*args, **kwargs)

        # Process Tags into choices (lists of tuples)
        self.fields['availableTags'].choices = tags
        self.conn = conn