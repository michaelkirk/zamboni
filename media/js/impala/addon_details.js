$(function () {
    $('.performance-note .popup').each(function(i,p) {
        var $p = $(this),
            $a = $p.siblings('a').first();
        $p.popup($a, {width: 300, pointTo: $a});
    });
    $('.item.addon').each(function(i,p){
        var $this = $(this);
        if ($this.find('.concealed').length == $this.find('.button').length) {
            $this.addClass('incompatible');
        }
    });
    $(document.body).bind('newStatic', function() {
        $('.install-note:visible').closest('.item').addClass('static');
    }).bind('closeStatic', function() {
        $('.item.static').removeClass('static');
    });

    if (!$("body").hasClass('addon-details')) return;
    $(".previews").zCarousel({
        btnNext: ".previews .next",
        btnPrev: ".previews .prev",
        itemsPerPage: 3
    });
    (function() {
        var $document = $(document),
            $lightbox = $("#lightbox"),
            $content = $("#lightbox .content"),
            $caption = $("#lightbox .caption span"),
            current, $strip,
            lbImage = template('<img id="preview{0}" src="{1}">');
        if (!$lightbox.length) return;
        function showLightbox() {
            $lightbox.show();
            showImage(this);
            $(window).bind('keydown.lightboxDismiss', function(e) {
                switch(e.which) {
                    case 27:
                        hideLightbox();
                        break;
                    case 37:
                        showPrev();
                        break;
                    case 39:
                        showNext();
                        break;
                }
            });
            //I want to ensure the lightbox is painted before fading it in.
            setTimeout(function () {
                $lightbox.addClass("show");
            },0);
        }
        function hideLightbox() {
            $lightbox.removeClass("show");
            // We can't trust transitionend to fire in all cases.
            setTimeout(function() {
                $lightbox.hide();
            }, 500);
            $(window).unbind('keydown.lightboxDismiss');
        }
        function showImage(a) {
            var $a = $(a),
                $oldimg = $lightbox.find("img");
            current = $a.parent().index();
            $strip = $a.closest("ul").find("li");
            var $img = $("#preview"+current);
            if ($img.length) {
                $oldimg.css("opacity", 0);
                $img.css({
                    "opacity": 1,
                    'margin-top': (525-$img.height())/2+'px',
                    'margin-left': (700-$img.width())/2+'px'
                });
            } else {
                $img = $(lbImage([current, $a.attr("href")]));
                $content.append($img);
                $img.load(function(e) {
                    $oldimg.css("opacity", 0);
                    $img.css({
                        "opacity": 1,
                        'margin-top': (525-$img.height())/2+'px',
                        'margin-left': (700-$img.width())/2+'px'
                    });
                    for (var i=0; i<$strip.length; i++) {
                        if (i != current) {
                            var $p = $strip.eq(i).find("a");
                            $content.append(lbImage([i, $p.attr("href")]));
                        }
                    }
                });
            }
            $caption.text($a.attr("title"));
            $lightbox.find(".control").removeClass("disabled");
            if (current < 1) {
                $lightbox.find(".control.prev").addClass("disabled");
            }
            if (current == $strip.length-1){
                $lightbox.find(".control.next").addClass("disabled");
            }
        }
        function showNext() {
            if (current < $strip.length-1) {
                showImage($strip.eq(current+1).find("a"));
                $(this).blur();
            }
        }
        function showPrev() {
            if (current > 0) {
                showImage($strip.eq(current-1).find("a"));
                $(this).blur();
            }
        }
        $("#lightbox .next").click(_pd(showNext));
        $("#lightbox .prev").click(_pd(showPrev));
        $(".previews ul a").click(_pd(showLightbox));
        $('#lightbox').click(_pd(function(e) {
            if ($(e.target).is('.close, #lightbox')) {
                hideLightbox();
            }
        }));
    })();

    if ($('#more-webpage').exists()) {
        var $moreEl = $('#more-webpage');
            url = $moreEl.attr('data-more-url');
        $.get(url, function(resp) {
            var $newContent = $(resp);
            $moreEl.replaceWith($newContent);
            $newContent.find('.listing-grid h3').truncate( {dir: 'h'} );
            $newContent.find('.install').installButton();
            $newContent.find('.listing-grid').each(listing_grid);
            $('#reviews-link').addClass('scrollto').attr('href', '#reviews');
        });
    }

    if ($('#review-add-box').exists())
        $('#review-add-box').modal('#add-review', { delegate: '#page', width: '650px' });

    if ($('#privacy-policy').exists())
        $('#privacy-policy').modal('.privacy-policy', { width: '500px' });

    // Show add-on ID when icon is clicked
    if ($("#addon[data-id], #persona[data-id]").exists()) {
        $("#addon .icon").click(function() {
            window.location.hash = "id=" + $("#addon, #persona").attr("data-id");
        });
    }

    $('#abuse-modal').modal('#report-abuse', {delegate: '#page'});
});
