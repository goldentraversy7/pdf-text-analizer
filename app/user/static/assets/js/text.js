function SetTitle(str) {
  $("#text_save_title")[0].value = str;
}

function OpenText(title) {
  $.ajax({
    url: "/api/set/state",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({ title: title }),
    success: function (list) {
      location.reload();
    },
    error: function (xhr) {
      var error_response = JSON.parse(xhr.responseText);
      showToast(error_response.message);
    },
  });
}

$(document).ready(function () {
  // Definition
  let is_upload;
  let is_stopped;
  var res_summer_element = document.getElementById("resultados_summernote");
  // res_summer_element.summernote({
  //     tabsize: 2,
  //     height: 100
  // });

  // Init variation

  function init() {
    return $.ajax({
      type: "POST",
      url: "/api/get/state",
      success: function (data) {
        console.log(data);
        $("#text #title")[0].innerHTML = data?.title || "No title";
        $("#hole_pdf_viewer").attr(
          "src",
          data.file_name ? "/api/pdf/" + data.file_name : ""
        );
        $("#summary_text")[0].innerHTML = marked.parse(data?.pdf_resume || "");
        $("#summary_preloader").hide();
        $(".preloader.sub").hide();

        $("#pdf_file")[0].value = "";
        stopBtnRevert();
      },
      error: function (xhr, status, error) {},
      beforeSend: function () {
        $("#summary_preloader").show();
      },
      statusCode: {
        401: function () {
          window.location.href = "/login";
        },
      },
    });

    is_upload = false;
    is_stopped = false;
  }

  function stopBtnRevert() {
    $(".text_stopbtn").text("Stop");
    $(".text_stopbtn").prop("disabled", false);
    is_stopped = false;
  }
  // Ajax Function Group

  function ajax_reset() {
    return $.ajax({
      type: "POST",
      url: "/api/reset",
      beforeSend: function () {
        $("#preloader").show();
      },
      success: function (response) {
        console.log(response);
      },
      error: function (xhr, status, error) {
        // Handle errors
        console.error("Error occur:", status, error);
      },
      complete: function () {
        $("#preloader").hide();
      },
    });
  }

  function ajax_uploadfile(form_data) {
    return $.ajax({
      type: "POST",
      url: "/api/uploadfile",
      data: form_data,
      contentType: false,
      cache: false,
      processData: false,
      beforeSend: function () {
        $("#pdf_viewer_preloader").show();
      },
      success: function (response) {
        console.log(response);
        is_upload = true;
        const response_file = response.message;
        $("#hole_pdf_viewer").attr(
          "src",
          "/api/pdf/" + response_file["file_path"]
        );
      },
      statusCode: {
        401: function () {
          window.location.href = "/login";
        },
      },
      error: function (xhr, status, error) {
        console.error("Error occur:", status, error);
      },
      complete: function () {
        $("#pdf_viewer_preloader").hide();
      },
    });
  }

  function ajax_summary(is_reload) {
    return $.ajax({
      type: "POST",
      url: "/api/analysis_pdf",
      success: function (response) {
        $("#summary_preloader").hide();
        $("#summary_text")[0].innerHTML = marked.parse(response.message);

        stopBtnRevert();
      },
      error: function (xhr, status, error) {},
      beforeSend: function () {
        $("#summary_preloader").show();
      },
      statusCode: {
        401: function () {
          window.location.href = "/login";
        },
      },
    })
      .done(function (response) {
        if (is_reload) return;
        else return;
      })
      .fail(function (xhr, status, error) {
        if (is_stopped) {
          $("#summary_preloader").hide();

          stopBtnRevert();
          return;
        } else {
          setTimeout(() => {
            return ajax_summary(false);
          }, 10000);
        }
      });
  }

  // Button Group

  $("#reset").on("click", function (event) {
    ajax_reset().done(function () {
      init();
    });
  });

  $("#pdf_file").on("change", function (event) {
    var form_data = new FormData($("#file_upload_form")[0]);
    ajax_uploadfile(form_data);
  });

  $("#analysis").on("click", function (event) {
    if (is_upload) {
      $("#analysis").prop("disabled", true);
      $("#reset").prop("disabled", true);
      ajax_summary(false);
    } else {
      alert("Select the PDF file");
    }
  });

  // Stop buttons

  $(".text_stopbtn").on("click", function (event) {
    event.preventDefault();

    is_stopped = true;
    $(this).text("Stoping");
    $(this).prop("disabled", true);
  });

  // Reload buttons

  $("#summary_reload").on("click", function (event) {
    ajax_summary(true);
  });

  init();
});
