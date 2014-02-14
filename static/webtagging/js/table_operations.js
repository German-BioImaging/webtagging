if (typeof OME === "undefined"){
    var OME = {}
}

/**
 * Performs an operation on a tab table column
 * @param {object} th - The column header of the column to operate on, or a child of the same
 * @param {function} op - The operation to execute. Must be able to handle td and th elements. Must have its scope bound.
                          e.g. OME.column_operation($th, function(cell) { $(cell).remove(); });
 */
OME.column_operation = function(th, op) {
    // Create variables holding all the th elements so that this can be used to calculate the index
    var $ths = $('#token-table > thead > tr > th');
    var $rows = $('#token-table > tbody > tr');
    var $th = $(th);

    // Get the th parent element if it is not directly specified
    if (!$th.is('th')) {
        $th = $th.parents('th');
    }

    // Get the position of the th element in which the selector is
    var colIndex = $ths.index( $th );

    // For each row
    $rows.each(function(i, v){
        // Get the td for each row
        var $td = $(v).children().eq(colIndex);
        // Perform the operation on each td
        op($td);
    });
    // Perform the operation on the th
    op($th);
}