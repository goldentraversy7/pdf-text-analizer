$(document).ready(function () {
  $("#user_register").on("click", function () {
    const givenName = $("#register-form #givenName")[0].value;
    const familyName = $("#register-form #familyName")[0].value;
    const email = $("#register-form #email")[0].value;
    const pwd = $("#register-form #password")[0].value;

    $.ajax({
      url: "register/users",
      type: "POST",
      data: { givenName, familyName, email, pwd },
      success: function (response) {
        window.location.href = "/login";
      },
      error: function (xhr, status, error) {
        const response = JSON.parse(xhr.responseText);
        showToast(response.message, "danger");
        console.log("Error: " + response);
      },
    });
  });
});
