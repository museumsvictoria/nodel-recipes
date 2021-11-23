/**
 * Created by Michael on 21/07/2015.
 */
// set global ajax timeout and disable cache
$.ajaxSetup({timeout: 30000, cache: false});

// customised jquery ajax function for posting JSON
$.postJSON = function(url, data, callback) {
  return jQuery.ajax({
    'type': 'POST',
    'url': url,
    'contentType': 'application/json',
    'data': data,
    'dataType': 'json',
    'success': callback
  });
};

var parseType = function(val, type) {
  switch(type){
    case "number":
      return parseFloat(val);
    case "string":
      return String(val);
    case "boolean":
      return Boolean(val);
  };
  return val;
}

var stringify = function(arg, type) {
  if($.isPlainObject(arg)) return JSON.stringify(arg);
  else if(type=="string") return '"'+arg+'"';
  else return arg;
};

navigator.issmart = (function(){
  var ua= navigator.userAgent;
  x= ua.match(/SMART-TV|ADAPI/i) ? true: false;
  return x;
})();

var updatepadding = function() {
  $('body').css('padding-top',  $('nav.navbar-fixed-top').outerHeight() + 20);
  $('body.hasfooter').css('padding-bottom',  $('footer.navbar-fixed-bottom').outerHeight() + 50);
};

var updatemeter = function(ele, arg) {
  if(!_.isFunction($(ele).data('throttle'))) {
    $(ele).data('throttle', _.throttle(function(el, val) {
      var pxheight = $(el).data('pxheight');
      if(!pxheight) {
        var pxheight = $(el).find('.bar').height() / 100;
        $(el).data('pxheight', pxheight);
      }
      var width = $(el).data('width');
      if(!width) {
        var width = $(el).find('.bar').width();
        $(el).data('width', width);
      }
      var bar = $(el).data('bar');
      if(!bar) {
        var bar = $(el).find('.bar');
        $(el).data('bar', bar);
      }
      var range = $(el).data('range');
      if(range=='db') var vl = 88*Math.pow(10,val/40);
      else var vl = val;
      if(vl > 100) vl = 100;
      if(vl < 0) vl = 0;
      $(bar).css('clip', 'rect('+((100-vl) * pxheight)+'px, '+width+'px, 100px, 0px)');
      var p = $(el).data('p');
      if(!p) {
        var p = $(el).find('p');
        $(el).data('p', p);
      }
      $(p).text(Math.floor(val));
    }, 100));
  }
  $(ele).data('throttle')(ele, arg);
};

var updatesignal = function(ele, arg) {
  if(!_.isFunction($(ele).data('throttle'))) {
    $(ele).data('throttle', _.throttle(function(el, val) {
      var range = $(el).data('range');
      if(range=='db') var vl = 88*Math.pow(10,val/40);
      else var vl = val;
      if(vl > 100) vl = 100;
      if(vl < 0) vl = 0;
      $(ele).attr('class', function(i, c){
        return c && c.replace(/\bmeter-colour-\S+/g, 'meter-colour-'+Math.round(vl));
      });
    }, 100));
  }
  $(ele).data('throttle')(ele, arg);
};
var node = host = opts = '';
var converter = new Markdown.Converter();
var unicodematch = new XRegExp("[^\\p{L}\\p{N}]", "gi");

$(function() {
  host = document.location.hostname + ':' + window.document.location.port;
  opts = {"local": {"event": {"colour": "#ff6a00","icon":"&#x25b2;"},"action":{"colour":"#9bed00","icon":"&#x25ba;"}}, "remote": {"event": {"colour":"#ce0071","icon":"&#x25bc;"},"action":{"colour":"#00a08a","icon":"&#x25c4;"},"eventBinding": {"colour":"#ce0071","icon":"&#x2194;"},"actionBinding":{"colour":"#00a08a","icon":"&#x2194;"}}, "unbound": {"event": {"colour":"#ce0071","icon":"&#x25ac;"},"action":{"colour":"#00a08a","icon":"&#x25ac;"}}};
  if(navigator.issmart){
    $('head').append('<style>.fixed-table-body{overflow-y: hidden;} body{zoom: 140%}</style>');
  };
  updatepadding();
  // get the node name
  if(window.location.pathname.split( '/' )[1]=="nodes") node = decodeURIComponent(window.location.pathname.split( '/' )[2].replace(/\+/g, '%20'));
  if(node) {
    convertNames();
    setEvents();
    updateLogs();
    checkReload();
  }
  // selecct first page
  $('*[data-nav]').first().trigger('click');
  // init scrollable divs
  $('.scrollbar-inner').scrollbar();
  // hide sects by default
  $(".sect").hide();
});

var checkReload = function(){
  var params = {};
  if(!_.isUndefined($('body').data('timestamp'))) params = {timestamp:$('body').data('timestamp')};
  $.getJSON('http://'+host+'/REST/nodes/'+encodeURIComponent(node)+'/hasRestarted', params, function(data) {
    if(_.isUndefined($('body').data('timestamp'))){
      $('body').data('timestamp', data.timestamp);
    } else if ($('body').data('timestamp')!=data.timestamp) {
      window.location.reload();
    }
  }).always(function() {
    $('body').data('timer', setTimeout(function() { checkReload(); }, 5000));
  });
};

var convertNames = function(){
  $.each($("[data-showevent]"), function () {
    $(this).data('showevent', $.map($.isArray($(this).data('showevent')) ? $(this).data('showevent') : [$(this).data('showevent')], function(at){
      return at.replace(unicodematch,'');
    }));
  });
  $.each($("[data-event]"), function () {
    $(this).data('event', $.map($.isArray($(this).data('event')) ? $(this).data('event') : [$(this).data('event')], function(at){
      return at.replace(unicodematch,'');
    }));
  });
  $.each($("[data-status]"), function () {
    $(this).data('status', $.map($.isArray($(this).data('status')) ? $(this).data('status') : [$(this).data('status')], function(at){
      return at.replace(unicodematch,'');
    }));
  });
  $.each($("[data-render]"), function () {
    $(this).data('render', $.map($.isArray($(this).data('render')) ? $(this).data('render') : [$(this).data('render')], function(at){
      return at.replace(unicodematch,'');
    }));
  });
}

var setEvents = function(){
  $(window).on('resize', function () {
    updatepadding();
  });
  $(window).on('orientationchange', function () {
    if(!_.isUndefined(window.navigator.standalone) && window.navigator.standalone){
      setTimeout(function(){ updatepadding(); }, 200);
    }
  });
  $('body').on('touchend touchcancel',':not(input)', function (e) {
    if(navigator.issmart) $('body').removeClass('touched');
  });
  $('body').on('touchstart',':not(input)', function (e) {
    if(navigator.issmart) $(this).trigger('click');
  });
  $('body').on('input','input[type=range]input[data-action]', function (e){
    var ele = $(this);
    data = getAction(this);
    if(!_.isFunction($(this).data('throttle'))) {
      $(ele).data('throttle', _.throttle(function(act, ar) {
        callAction(act, ar);
      }, 250));
    }
    $(ele).data('throttle')(data.action, data.arg);
  });
  $('body').on('touchstart mousedown touchend touchcancel mouseup','*[data-actionon]*[data-actionoff]', function (e) {
    e.stopPropagation(); e.preventDefault();
    data = getAction(this);
    if($.inArray(e.type, ['touchstart','mousedown']) > -1) $(this).addClass('active');
    else $(this).removeClass('active');
    callAction(data.action, data.arg);
  });
  $('body').on('click','*[data-arg], *[data-action]', function (e) {
    e.stopPropagation(); e.preventDefault();
    if(!$('body').hasClass('touched')) {
      if(navigator.issmart) $('body').addClass('touched');
      data = getAction(this);
      if(data.action) {
        if(data.confirm){
          $('#confirmlabel').text(data.confirmtitle);
          $('#confirmtext').text(data.confirmtext);
          $('#confirmaction').data('confirmaction', data.action);
          $('#confirmaction').data('arg', data.arg);
          if((data.confirm == 'code') && ($('#confirmcodesrc').val().length)) {
            $('#confirmkeypad').show();
            $('#confirmaction').attr('disabled','disabled');
          } else {
            $('#confirmkeypad').hide();
            $('#confirmaction').removeAttr('disabled');
          }
          $('#confirm').modal('show');
        } else callAction(data.action, data.arg);
        $(this).parents('.btn-select.open').find('.dropdown-toggle').dropdown('toggle');
      }
    }
  });
  $('body').on('click','#confirmaction', function (e) {
    e.stopPropagation(); e.preventDefault();
    if(!$('body').hasClass('touched')) {
      if(navigator.issmart) $('body').addClass('touched');
      callAction($(this).data('confirmaction'), $(this).data('arg'));
      $('#confirm').modal('hide');
    };
  });
  $('body').on('click','*[data-link-event]', function (e) {
    e.stopPropagation(); e.preventDefault();
    var ele = $(this);
    var newWindow = window.open('http://'+host);
    $.getJSON('http://'+host+'/REST/nodes/'+encodeURIComponent(node)+'/remote', function(data) {
      if (!_.isUndefined(data['events'][$(ele).data('link-event')])) {
        var lnode = data['events'][$(ele).data('link-event')]['node'];
        if(lnode!==''){
          newWindow.location = 'http://'+host+'/?filter='+lnode;
          $.getJSON('http://'+host+'/REST/nodeURLsForNode',{'name':lnode}, function(data) {
            if (!_.isUndefined(data[0]['address'])){
              newWindow.location = data[0]['address'];
            }
          });
        }
      }
    });
  });
  $('body').on('click','*[data-link-url]', function (e) {
    e.stopPropagation(); e.preventDefault();
    window.open($(this).data('link-url'));
  });
  $('body').on('click', '*[data-nav]', function (e) {
    $('*[data-nav]').parents('li').removeClass('active');
    $('*[data-nav="'+$(this).data('nav')+'"]').parents('li').addClass('active');
    $("[data-section]").hide();
    $("[data-section="+$(this).data('nav')+"]").show();
  });
  $('body').on('click', '#confirmkeypad *[data-keypad]', function () {
    var number = $(this).data('keypad');
    if(number==-1){
      $("#confirmcode").val(function() {
        return this.value.slice(0, -1);
      });
    } else {
      $("#confirmcode").val(function() {
          return this.value + number;
      });
    }
    if($("#confirmcode").val() == $("#confirmcodesrc").val()) $('#confirmaction').removeAttr('disabled');
    else $('#confirmaction').attr('disabled','disabled');
  });
  $('#confirm').on('hidden.bs.modal', function () {
    $("#confirmcode").val('');
  });
};

var getAction = function(ele){
  var arg = '';
  var action = '';
  var confirm = false;
  var confirmtitle = 'Confirm';
  var confirmtext = 'Are you sure you would like to continue?';
  if (!_.isUndefined($(ele).data('arg-type'))) var type = $(ele).data('arg-type')
  else type = false;
  if (!_.isUndefined($(ele).data('actionon')) && !_.isUndefined($(ele).data('actionoff'))) {
    if ($(ele).hasClass('active')) action = $(ele).data('actionoff');
    else action = $(ele).data('actionon');
    if(!_.isUndefined($(ele).data('confirm'))) {
      confirm = $(ele).data('confirm');
      if(!_.isUndefined($(ele).data('confirmtitle'))) confirmtitle = $(ele).data('confirmtitle');
      if(!_.isUndefined($(ele).data('confirmtext'))) confirmtext = $(ele).data('confirmtext');
    }
  }
  else if (!_.isUndefined($(ele).data('action'))) {
    action = $(ele).data('action');
    if(!_.isUndefined($(ele).data('confirm'))) {
      confirm = $(ele).data('confirm');
      if(!_.isUndefined($(ele).data('confirmtitle'))) confirmtitle = $(ele).data('confirmtitle');
      if(!_.isUndefined($(ele).data('confirmtext'))) confirmtext = $(ele).data('confirmtext');
    }
  }
  else if (!_.isUndefined($(ele).closest('[data-arg-action]').data('arg-action'))) {
    action = $(ele).closest('[data-arg-action]').data('arg-action');
    if(!_.isUndefined($(ele).closest('[data-arg-action]').data('confirm'))) confirm = $(ele).closest('[data-arg-action]').data('confirm');
    if(!_.isUndefined($(ele).closest('[data-arg-action]').data('confirmtitle'))) confirmtitle = $(ele).closest('[data-arg-action]').data('confirmtitle');
    if(!_.isUndefined($(ele).closest('[data-arg-action]').data('confirmtext'))) confirmtext = $(ele).closest('[data-arg-action]').data('confirmtext');
  }
  if (!_.isUndefined($(ele).data('arg-on')) && !_.isUndefined($(ele).data('arg-off'))) {
    if ($(ele).hasClass('active')) arg = stringify({'arg': parseType($(ele).data('arg-off'), type)});
    else arg = stringify({'arg': parseType($(ele).data('arg-on'), type)});
  } else {
    if (!_.isUndefined($(ele).data('arg'))) arg = stringify({'arg':parseType($(ele).data('arg'), type)});
    else if(!_.isUndefined($(ele).data('arg-source'))) {
      if($(ele).data('arg-source') == 'this') val = parseType($(ele).val(), type);
      else val = parseType($($(ele).data('arg-source')).data('arg'), type);
      if(_.isUndefined(val)) val = {};
      if(!_.isUndefined($(ele).data('arg-sourcekey'))) {
        arg = {"arg":{}};
        arg['arg'][$(ele).data('arg-sourcekey')] = val;
        if(!_.isUndefined($(ele).data('arg-add'))) arg = $.extend(true, arg, {'arg': parseType($(ele).data('arg-add'), type)});
        arg = stringify(arg);
      } else arg = stringify({'arg':val});
    } else arg = "{}";
  }
  return {'action': action, 'arg': arg, 'confirm': confirm, 'confirmtitle': confirmtitle, 'confirmtext': confirmtext};
}

var callAction = function(action, arg) {
  $.each($.isArray(action) ? action : [action], function(i, act){
    $.postJSON('http://' + host + '/REST/nodes/' + node + '/actions/' + encodeURIComponent(act) + '/call', arg, function () {
      console.log(act + " - Success");
    }).fail(function (e, s) {
      errtxt = s;
      if (e.responseText) errtxt = s + "\n" + e.responseText;
      console.log("exec - Error:\n" + errtxt, "error");
    });
  });
};

var updateLogs = function(){
  if(!("WebSocket" in window)){
    console.log('using poll');
    var url;
    if (typeof $('body').data('seq') === "undefined") url = 'http://' + host + '/REST/nodes/' + encodeURIComponent(node) + '/activity?from=-1';
    else url = 'http://' + host + '/REST/nodes/' + encodeURIComponent(node) + '/activity?from=' + $('body').data('seq');
    $.getJSON(url, function (data) {
      if (typeof $('body').data('seq') === "undefined") {
        $('body').data('seq', -1);
      }
      data.sort(function (a, b) {
        return a.seq < b.seq ? -1 : a.seq > b.seq ? 1 : 0;
      });
      $.each(data, function (key, value) {
        if (value.seq != 0) {
          $('body').data('seq', value.seq + 1);
          parseLog(value);
        }
      });
    }).always(function () {
      $('body').data('logs', setTimeout(function () {
        updateLogs();
      }, 1000));
    });
  } else {
    $.getJSON('http://'+host+'/REST/nodes/' + encodeURIComponent(node), function(data){
      var wshost = "ws://"+document.location.hostname+":"+data['webSocketPort']+"/nodes/"+node;
      try{
        var socket = new WebSocket(wshost);
        socket.onopen = function(){
          console.log('Socket Status: '+socket.readyState+' (open)');
          online(socket);
        }
        socket.onmessage = function(msg){
          var data = JSON.parse(msg.data);
          //console.log('Received:');
          //console.log(data);
          if('activityHistory' in data){
            $.each(data['activityHistory'], function() {
              parseLog(this);
            });
          } else parseLog(data['activity']);
        }
        socket.onclose = function(){
          console.log('Socket Status: '+socket.readyState+' (Closed)');
          offline();
        }
      } catch(exception){
        console.log('Error: '+exception);
        offline();
      }
    }).fail(function(){
      console.log('Error reading configuration (getJSON failed)');
      offline();
    });
  }
};

var online = function(socket){
  $('body').data('timeout', setInterval(function() { socket.send('{}'); }, 1000));
  $('#offline').modal('hide');
};

var offline = function(){
  $('.modal').modal('hide');
  $('#offline').modal('show');
  clearInterval($('body').data('timeout'));
  $('body').data('update', setTimeout(function() { updateLogs(); }, 1000));
};

var parseLog = function(log){
  if(log.type=='event' && log.source=='local'){
    switch(log.alias) {
      case "Title":
        $('#title, title').text(log.arg)
        console.log(log.arg);
        break;
      case "Clock":
        var time = moment(log.arg).utcOffset(log.arg);
        $('#clock').data('time',time).text(time.format('h:mm:ss a'));
        break;
      default:
        // handle show-hide events
        var eles = $("[data-showevent]").filter(function() {
          return $.inArray(log.alias, $.isArray($(this).data('showevent')) ? $(this).data('showevent') : [$(this).data('showevent')]) >= 0;
        });
        $.each(eles, function (i, ele) {
          if ($(ele).hasClass('sect')) {
            if($.type(log.arg)== "object") log.arg = log.arg[$(ele).data('showevent-arg')];
            switch ($.type(log.arg)) {
              case "string":
                $(ele).hide();
                $(ele).filter(function() {
                  return $.inArray(log.arg, $.isArray($(this).data('showarg')) ? $(this).data('showarg') : [$(this).data('showarg')]) >= 0;
                }).show();
                break;
              case "boolean":
                $(ele).hide();
                if(_.isUndefined($(ele).data('showeventdata'))) $(ele).data('showeventdata', {});
                var val = $(ele).data('showeventdata');
                val[log.alias] = log.arg;
                $(ele).data('showeventdata', val);
                $.each($(ele).data('showeventdata'), function(i, e){
                  if(e == true) $(ele).show();
                });
                break;
            };
          }
        });
        if(eles.length) updatepadding();
        // handle event data updates
        var eles = $("[data-event]").filter(function() {
          return $.inArray(log.alias, $.isArray($(this).data('event')) ? $(this).data('event') : [$(this).data('event')]) >= 0;
        });
        $.each(eles, function (i, ele) {
          if($.type(log.arg)== "object") log.arg = log.arg[$(ele).data('event-arg')];
          if($(ele).hasClass('dynamic')) {
            $(ele).data('dynamic',log);
          }
          switch ($.type(log.arg)) {
            case "number":
              if ($(ele).not('.meter, .signal').is("div")) {
                $(ele).children().filter(function () {
                  return $(this).attr("data-arg") > log.arg;
                }).removeClass('btn-success').addClass('btn-default');
                $(ele).children().filter(function () {
                  return $(this).attr("data-arg") <= log.arg;
                }).removeClass('btn-default').addClass('btn-success');
              } else if ($(ele).is(".meter")) {
                updatemeter(ele, log.arg);
              } else if ($(ele).is(".signal")) {
                updatesignal(ele, log.arg);
              } else if($(ele).is("input")) {
                $(ele).not(':active').val(log.arg);
              } else {
                if ($(ele).is("output, span, h4, p")) $(ele).text(log.arg);
                // lists
                $(ele).children('li').has('a[data-arg]').removeClass('active');
                $(ele).children('li').has('a[data-arg="' + log.arg + '"]').addClass('active');
                // button select
                $(ele).parents('.btn-select').children('button').children('span:first-child').text($(ele).children('li').has('a[data-arg="' + log.arg + '"]').text());
                // pages
                $("[data-page]").hide();
                $('[data-page="' + log.arg + '"]').show();
                if($(ele).is("input")) $(ele).not(':active').val(log.arg);
              }
              break;
            case "string":
              if($(ele).hasClass('btn-pswitch')){
                var arg = log.arg.toLowerCase().replace(/[^a-z]+/gi, "");
                switch (arg) {
                  case "on":
                    $(ele).children('[data-arg="On"]').removeClass('active').addClass($(ele).data('class-on')).removeClass('btn-default').removeClass('btn-warning');
                    $(ele).children('[data-arg="Off"]').addClass('active').addClass('btn-default').removeClass($(ele).data('class-off')).removeClass('btn-warning');
                    break
                  case "off":
                    $(ele).children('[data-arg="Off"]').removeClass('active').addClass($(ele).data('class-off')).removeClass('btn-default').removeClass('btn-warning');
                    $(ele).children('[data-arg="On"]').addClass('active').addClass('btn-default').removeClass($(ele).data('class-on')).removeClass('btn-warning');
                    break;
                  case "partiallyon":
                    $(ele).children('[data-arg="On"]').removeClass('active').addClass('btn-warning').removeClass('btn-default').removeClass($(ele).data('class-on'));
                    $(ele).children('[data-arg="Off"]').addClass('active').addClass('btn-default').removeClass($(ele).data('class-off')).removeClass('btn-warning');
                    break
                  case "partiallyoff":
                    $(ele).children('[data-arg="Off"]').removeClass('active').addClass('btn-warning').removeClass('btn-default').removeClass($(ele).data('class-off'));
                    $(ele).children('[data-arg="On"]').addClass('active').addClass('btn-default').removeClass($(ele).data('class-on')).removeClass('btn-warning');
                    break;
                }
              } else if ($(ele).hasClass('label-pbadge')) {
                var arg = log.arg.toLowerCase().replace(/[^a-z]+/gi, "");
                switch (arg) {
                  case "on":
                    $(ele).text($(ele).data('on'));
                    $(ele).addClass($(ele).data('class-on')).removeClass('label-default').removeClass('label-warning').removeClass($(ele).data('class-off'));
                    break;
                  case "off":
                    $(ele).text($(ele).data('off'));
                    $(ele).addClass($(ele).data('class-off')).removeClass('label-default').removeClass('label-warning').removeClass($(ele).data('class-on'));
                    break;
                  case "partiallyon":
                    $(ele).text($(ele).data('on'));
                    $(ele).addClass('label-warning').removeClass('label-default').removeClass($(ele).data('class-on')).removeClass($(ele).data('class-off'));
                    break;
                  case "partiallyoff":
                    $(ele).text($(ele).data('off'))
                    $(ele).addClass('label-warning').removeClass('label-default').removeClass($(ele).data('class-on')).removeClass($(ele).data('class-off'));
                    break;
                }
              } else if ($(ele).hasClass('scrollbar-inner')) {
                var arg = converter.makeHtml(log.arg);
                $(ele).html(arg);
              } else {
                if ($(ele).is("span, h4, p")) $(ele).text(log.arg);
                // lists
                $(ele).children('li').has('a[data-arg]').removeClass('active');
                $(ele).children('li').has('a[data-arg="' + log.arg + '"]').addClass('active');
                // button select
                $(ele).parents('.btn-select').children('button').children('span:first-child').text($(ele).children('li').has('a[data-arg="' + log.arg + '"]').text());
                // pages
                $("[data-page]").hide();
                $('[data-page="' + log.arg + '"]').show();
                if($(ele).is("input")) $(ele).not(':active').val(log.arg);
                // image
                if ($(ele).is("img")) $(ele).attr("src", log.arg);
              }
              break;
            case "boolean":
              if($(ele).hasClass('btn-switch')) {
                if (log.arg) {
                  $(ele).children('[data-arg=true]').addClass($(ele).data('class-on')).removeClass('btn-default');
                  $(ele).children('[data-arg=false]').addClass('btn-default').removeClass($(ele).data('class-off'));
                } else {
                  $(ele).children('[data-arg=false]').addClass($(ele).data('class-off')).removeClass('btn-default');
                  $(ele).children('[data-arg=true]').addClass('btn-default').removeClass($(ele).data('class-on'));                  
                }
              } else if($(ele).is("a.btn")) {
                if (log.arg) $(ele).addClass($(ele).data('class-on')).addClass('active').removeClass('btn-default');
                else $(ele).addClass('btn-default').removeClass('active').removeClass($(ele).data('class-on'));
              }
              break;
            case "undefined":
              if($(ele).is("span, h4, p, output")) $(ele).text('');
              else if($(ele).is("input")) $(ele).not(':active').val('');
              break;
          }
        });
        var eles = $("[data-status]").filter(function() {
          return $.inArray(log.alias, $.isArray($(this).data('status')) ? $(this).data('status') : [$(this).data('status')]) >= 0;
        });
        $.each(eles, function (i, ele) {
          var ele = $(ele);
          var clstype = ele.hasClass('panel') ? 'panel' : 'label';
          if(!_.isUndefined(log.arg) && !_.isUndefined(log.arg['level']) && _.isNumber(log.arg['level'])){
            var msg = '';
            if(!_.isUndefined(log.arg['message']) && _.isString(log.arg['message'])) msg = log.arg['message'];
            ele.find('.status').not('[data-status]').text(msg);
            if(ele.hasClass('status')) ele.text(msg);
            switch(log.arg['level']) {
              case 0:
                ele.removeClass(clstype+'-default '+clstype+'-warning '+clstype+'-danger '+clstype+'-primary').addClass(clstype+'-success');
                break;
              case 1:
                ele.removeClass(clstype+'-default '+clstype+'-success '+clstype+'-danger '+clstype+'-primary').addClass(clstype+'-warning');
                break;
              case 2:
              case 3:
              case 4:
                ele.removeClass(clstype+'-default '+clstype+'-success '+clstype+'-warning '+clstype+'-primary').addClass(clstype+'-danger');
                break;
              case 5:
                ele.removeClass(clstype+'-default '+clstype+'-success '+clstype+'-warning '+clstype+'-danger').addClass(clstype+'-primary');
                break;
            }
          } else if(_.isBoolean(log.arg)) {
            if (log.arg) $(ele).addClass(clstype+'-success').removeClass(clstype+'-default');
            else $(ele).addClass(clstype+'-default').removeClass(clstype+'-success');
          }
        });
        var eles = $("[data-render]").filter(function() {
          return $.inArray(log.alias, $.isArray($(this).data('render')) ? $(this).data('render') : [$(this).data('render')]) >= 0;
        });
        $.each(eles, function (i, ele) {
          if($(ele).data('render-template')) {
            try {
              $(ele).html($($(ele).data('render-template')).render(log));
              if(!_.isUndefined($(ele).data('dynamic'))) parseLog($(ele).data('dynamic'));
            } catch(err) {
              console.log(err.message);
            } finally {
              return true;
            }
          }
        });
    }
  }
};