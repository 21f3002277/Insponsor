setTimeout(function() {
    var alertNode = document.querySelector('.alert');
    if (alertNode) {
        var bsAlert = new bootstrap.Alert(alertNode);
        bsAlert.close();
    }
}, 3000); // 3000 milliseconds = 3 seconds