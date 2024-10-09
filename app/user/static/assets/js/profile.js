$(document).ready(function () {
  $("#save_profile_btn").on("click", function () {
    const given_name = $("#profile_form #given_name")[0].value;
    const family_name = $("#profile_form #family_name")[0].value;
    const phone_number = $("#profile_form #phone_number")[0].value;
    const address = $("#profile_form #address")[0].value;
    const old_pwd = $("#profile_form #old_pwd")[0].value;
    const new_pwd = $("#profile_form #new_pwd")[0].value;

    $.ajax({
      url: "profile/save",
      type: "POST",
      data: {
        given_name,
        family_name,
        phone_number,
        address,
        old_pwd,
        new_pwd,
      },
      success: function (response) {
        showToast("Profile updated successfully!", "success");
      },
      error: function (xhr, status, error) {
        const response = JSON.parse(xhr.responseText);
        showToast(response.message, "danger");
        console.log("Error: " + response);
      },
    });
  });
});
