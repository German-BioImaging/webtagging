if (typeof OME === "undefined"){
    var OME = {}
}
OME.show_tags_dialog = function(tags_url, success, options) {

    options = options || {};

    var title = 'Choose Tag';
    if (options.multiple) {
        title += "s";
    }
    if ($("#tag_chooser_form").length === 0) {
        $("<form id='tag_chooser_form'></form>")
            .attr('title', title)
            .hide().appendTo('body');
    }
    // set-up the tags form to use dialog
    $("#tag_chooser_form").dialog({
        autoOpen: true,
        resizable: false,
        height: 370,
        width:420,
        modal: true,
        buttons: {
            "Accept": function() {
                var rv = []
                $("#tag_chooser_select option:selected").each(function(){
                    var $select = $(this);
                    rv.push({'id':$select.attr('value'), 'name':$(this).text()});
                });
                success(rv);
                $( this ).dialog( "close" );
            },
            "Cancel": function() {
                $( this ).dialog( "close" );
                success();
            }
        },
        close: function() {
            $("#tag_chooser_form").dialog( "destroy" ).remove();
        }
    });

    // load form via AJAX...
    $("#tag_chooser_form").load(tags_url, function() {
        if (options.multiple) {
            $("#tag_chooser_select").attr('multiple', true);
        }
        $("#tag_chooser_select").chosen({placeholder_text:title, allow_single_deselect: true})
            .change(function(){
                console.log(arguments);
            });
        if (options.new_tag_default) {
            console.log(options.new_tag_default);
            $("#tag_chooser_new").val(options.new_tag_default);
        }
    });
}