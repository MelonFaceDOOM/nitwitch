function insertAtCursor(areaId, myValueBefore, myValueAfter) {
    var myField = document.getElementById(areaId);
    if (document.selection) {

        myField.focus();
        document.selection.createRange().text = myValueBefore + document.selection.createRange().text + myValueAfter;


    } else if (myField.selectionStart || myField.selectionStart == '0') {

        var startPos = myField.selectionStart;
        var endPos = myField.selectionEnd;
        myField.value = myField.value.substring(0, startPos)+ myValueBefore+ myField.value.substring(startPos, endPos)+ myValueAfter+ myField.value.substring(endPos, myField.value.length);
		myField.focus(); myField.selectionStart = startPos + myValueBefore.length; myField.selectionEnd = endPos + myValueBefore.length;

    }
}