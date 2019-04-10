/**
 * Created by eliasfernandez on 10/01/2017.
 */

// add 2 min
const interval = 2 * 60 * 1000;

$(document).ready(function () {
    var t_start = new Date();
    var deadline = new Date(Date.parse(t_start) + interval);
    initializeClock('countdown', deadline);
    $("#rdaction").submit(function () {
        var t_end = new Date();
        $('#roundends').val(t_end.toISOString());
        $('#roundstarts').val(t_start.toISOString());
        var time_elapsed = getTimeInterval(t_start, t_end);
        var seconds = ((t_end - t_start) / 1000) % 60;
        var std_elapsed_format = [time_elapsed.hours, time_elapsed.minutes, seconds].join(":");
        $('#timeelapsed').val(std_elapsed_format);
        var val = $("button[type=submit][clicked=true]").val();
        $('#actionhid').val(val);
    });
    $("form button[type=submit]").click(function () {
        $("input[type=submit]", $(this).parents("#rdaction")).removeAttr("clicked");
        $(this).attr("clicked", "true");
    });
});

function getTimeInterval(initialTime, endTime) {
    var t = Date.parse(endTime) - Date.parse(initialTime);
    var seconds = Math.floor((t / 1000) % 60);
    var minutes = Math.floor((t / 1000 / 60) % 60);
    var hours = Math.floor((t / (1000 * 60 * 60)) % 24);
    var days = Math.floor(t / (1000 * 60 * 60 * 24));
    return {
        'total': t,
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds
    };
}

function getTimeRemaining(endTime) {
    return getTimeInterval(new Date(), endTime)
}

function initializeClock(id, endtime) {
    var minutesSpan = $("#" + id + " .minutes");
    var secondsSpan = $("#" + id + " .seconds");

    function updateClock() {
        var t = getTimeRemaining(endtime);

        minutesSpan.html(('0' + t.minutes).slice(-2));
        secondsSpan.html(('0' + t.seconds).slice(-2));

        if (t.total <= 0) {
            clearInterval(timeinterval);
        }
    }

    updateClock();
    var timeinterval = setInterval(updateClock, 1000);
}