
$(document).ready(function() {
    $('.recommendations-actions').click(function(e) {
      e.preventDefault(); 
      var buttonName = $(this).attr('name');
      if (buttonName === 'regenerate-btn') {
        $('#loading-screen').show();
      }
      var id = "{{ id }}";
      var formData = $('#playlist-form').serialize() + '&' + buttonName + '=1&id=' + id;
      $.ajax({
        type: 'POST',
        url: '/create_playlist',
        data: formData,
        success: function(response) {
          if (buttonName === 'add-to-playlist-btn') {
            $('#message-container').text(response); 
          }
          else if (buttonName === 'regenerate-btn') {
            $('#loading-screen').hide();
            document.documentElement.innerHTML = response;
          }
        },
        error: function(error) {
          console.error('Error:', error);
        }
      });
    });
});
