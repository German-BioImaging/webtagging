from django.forms import Form, MultipleChoiceField, BooleanField


class TagSearchForm(Form):
    selectedTags = MultipleChoiceField()
    results_preview = BooleanField()

    def __init__(self, tags, conn=None, *args, **kwargs):
        super(TagSearchForm, self).__init__(*args, **kwargs)

        # Process Tags into choices (lists of tuples)
        self.fields["selectedTags"].choices = tags
        self.conn = conn
