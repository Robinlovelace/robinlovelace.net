(function ($, window, document) {
    'use strict';
    var agendaItems, agendaChannels, filters, currentDay, currentChannel;
    var History = window.History; // Note: We are using a capital H instead of a lower h
    function getActiveTags() {
        var activeButtons = $('[data-channel-day] a.active-channel');

        var values = $.map(activeButtons, function (element, index) { return $(element).attr('value'); });

        return values.join(',');
    }
    function buildUpQueryString(data) {
        var queryString = "";
        if (queryString.length > 0) queryString += "&";
        queryString += "AgendaId=" + data.AgendaId;
        if (queryString.length > 0) queryString += "&";
        queryString += "Channel=" + data.Channel;
        return "?" + queryString;
    }
    function getData(page) {
        var agendaId = $('#agendaId').val();
        var channel = getActiveTags();
        return {
            Channel: channel,
            AgendaId: agendaId,
            Page: page
        };
    }
    function updateResultsLogic(page) {
        var data = getData(page);
        History.pushState(data, $('title').html(), location.pathname + buildUpQueryString(data));
    }
    window.updateResults = function() {
        updateResultsLogic(1);
    };
    function updateTags(event) {
        $(event.target).toggleClass('active-channel').toggleClass('');
        event.preventDefault();
        window.updateResults();
    }
    //function handleShowChannel(e) {
    //    e.preventDefault();
    //    var $el = $(e.target);
    //    var channel = $el.data('channel');
    //    var active = showChannel(channel);
    //    $el.toggleClass('active-channel', active);
    //}
    function resetChannels() {
        $('[data-day]').find('[data-row-container]').show().find('li').show();
        //$('a[data-channel]').removeClass('active-channel');
    }
    //function showChannel(channel) {
    //    resetChannels();
    //    if (!channel || currentChannel === channel) {
    //        currentChannel = null;
    //        return false;
    //    }
    //    var table = $('[data-day="' + currentDay + '"]');
    //    table.find('[data-row-container]').hide()
    //        .find('li').hide()
    //        .filter('[data-channel="' + channel + '"]').show()
    //        .parents('[data-row-container]').show();
    //    currentChannel = channel;
    //    return true;
    //}
    //function changeDay(e) {
    //    var dayName = $(e.target).data('day');
    //    $('[data-channel-day]').hide()
    //        .filter('[data-channel-day="' + dayName + '"]').show();
    //    currentDay = dayName;
    //    resetChannels();
    //} 
    $(function () {
        agendaChannels = $('[data-channel]');
        agendaItems = $('[data-item-channel]');
        //$('a[data-toggle="tab"]').on('shown.bs.tab', changeDay).eq(0).click();
        //$('a[data-channel]').on('click', handleShowChannel);
        $('.agenda-tabs li:first-child').addClass("active");
        $('.tab-content .tab-pane:first-child').addClass("active");
        $(document).on('click', 'a.agenda-search-toggle', function (e) {
            var currentClass = $(this).parent('.agenda-search').attr('class');
            if (currentClass === "agenda-search is-expanded") {
                $(this).html('<span>Filters <span><i class="fa fa-arrow-up"></i></span></span>');
            } else {
                $(this).html('<span>Filters <span><i class="fa fa-arrow-down"></i></span></span>');
            }
            $(this).parent('.agenda-search').toggleClass("is-expanded");
        });
        //tags changes
        $(document).on('click', '[data-channel-day] a', updateTags);
        $(document).on('click', '[data-filters] a', function (e) {
            e.preventDefault();
            var currentValue = $(this).attr("value");
            $('[data-channel-day] a[value="' + currentValue + '"]').removeClass('active-channel');
            window.updateResults();
        });
        $(".iframe-fancybox").fancybox({
            autoSize: false,
            width: 1200,
            height: "800px",
            beforeLoad: function () {
                $('.agenda-search').removeClass('is-expanded');
                $('.agenda-search-toggle').html('<span>Filters <span><i class="fa fa-arrow-up"></i></span></span>');
                $('.addthis-smartlayers-desktop').attr("style", "display:none;");
            },
            afterClose: function() {
                $('.addthis-smartlayers-desktop').attr("style", "display:block;");
            }
        });
        
    });
    function reloadQuery() {
        var State = History.getState();
        $.ajaxSetup({ cache: false });
        $.get('/agenda/query', State.data, function (response) {
            $('#new-agenda-query-container').replaceWith(response);
        });
    }
    function markAsLoading() {
        $('#new-agenda-results-container').text('').html('<div class="spinner-con"><i class="fa fa-refresh fa-spin-custom"></i></div>');
    }
    // Bind to StateChange Event
    History.Adapter.bind(window, 'statechange', function () { // Note: We are using statechange instead of popstate#
        markAsLoading();
        reloadQuery();
        var State = History.getState();
        $.get('/agenda/results', State.data, function (response) {
            $('#new-agenda-results-container').replaceWith(response);
            $("html, body").animate({ scrollTop: 0 }, 100);
            $('.agenda-tabs li:first-child').addClass("active");
            $('.tab-content .tab-pane:first-child').addClass("active");
        });
    });
})(jQuery, window, document);




