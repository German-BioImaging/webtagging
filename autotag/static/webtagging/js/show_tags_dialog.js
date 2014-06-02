if (typeof OME === "undefined"){
    var OME = {}
}
OME.show_tags_dialog = function(options) {

    options = options || {};

    var title = 'Choose Tag';
    if (options.multiple) {
        title += "s";
    }
    if ($("#tag_chooser_form").length === 0) {
        $("<form id='tag_chooser_form' method='POST' action='"+ options.create_tag + "'></form>")
            .attr('title', title)
            .hide().appendTo('body');
    }
    var $tag_chooser_form = $("#tag_chooser_form")
    // set-up the tags form to use dialog
    $tag_chooser_form.dialog({
        autoOpen: true,
        resizable: false,
        height: 370,
        width:420,
        modal: true,
        buttons: {
            "OK": function() {
                var rv = []

                // If no tag is selected
                $selected = $("#tag_chooser_select option:selected");
                if ($selected.length === 0) {
                    var new_tag = $('#tag_chooser_new').val().toLowerCase();
                    var abort = false;
                    // Make sure it is not one of the currently used tags (they aren't in the available list)
                    if ($.inArray(new_tag, options.current_tag_names) != -1) {
                        abort = true;
                    } else {
                        // Make sure it is not in the available list already
                        $('#tag_chooser_select').children('option').each(function(k,v) {
                            if (new_tag === $(v).text().toLowerCase()) {
                                abort = true;
                            }
                        });
                    }

                    if (abort) {
                        var $standard_form = $('#tag_chooser_form > .standard_form');
                        var $create_tag_error = $standard_form.children('#create_tag_error').remove();
                        $standard_form.append('<div id="create_tag_error" style="color:red">Error, it is inadvisable (and impossible in this interface) to create a tag which already exists and is available for use!</div>');
                        return;
                    }

                }

                $("#tag_chooser_select option:selected").each(function(){
                    var $select = $(this);
                    rv.push({'id':$select.attr('value'), 'name':$(this).text(), 'desc':$select.data('desc'), 'owner':$select.data('owner')});
                });
                // If no existing tags are selected
                if (rv.length == 0) {
                    var new_tag = $('#tag_chooser_new').val();
                    if (new_tag.length > 0 && options.create_tag) {
                        $tag_chooser_form.submit();
                    }
                }
                // If there is a success function, call it
                else if (options.success) {
                    options.success(rv);
                    $( this ).dialog( "close" );
                }
            },
            "Cancel": function() {
                $( this ).dialog( "close" );
            }
        },
        close: function() {
            $tag_chooser_form.dialog( "destroy" ).remove();
        }
    });

    $("#tag_chooser_form").ajaxForm({
        dataType: 'json',
        success: function(data) {
            if (options.success) {
                options.success([data]);
            }
            $tag_chooser_form.dialog("close");
        }
    });

    // load form via AJAX...
    $("#tag_chooser_form").load(options.list_tags, {'current_tag_ids':options.current_tag_ids}, function() {
        if (options.multiple) {
            $("#tag_chooser_select").attr('multiple', true);
        }
        $("#tag_chooser_select").chosen({placeholder_text:title, allow_single_deselect: true})
            .change(function(){
                console.log(arguments);
            });
        if (options.new_tag_default) {
            $("#tag_chooser_new").val(options.new_tag_default);
        }
    });
}
