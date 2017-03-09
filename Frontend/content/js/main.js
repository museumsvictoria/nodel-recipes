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
      $(bar).css('clip', 'rect('+((100-val) * pxheight)+'px, '+width+'px, 100px, 0px)');
      var p = $(el).data('p');
      if(!p) {
        var p = $(el).find('p');
        $(el).data('p', p);
      }
      $(p).text(val);
    }, 100));
  }
  $(ele).data('throttle')(ele, arg);
}

var node = host = opts = '';
var converter = new Markdown.Converter();

$(function() {
  host = document.location.hostname + ':' + window.document.location.port;
  opts = {"local": {"event": {"colour": "#ff6a00","icon":"&#x25b2;"},"action":{"colour":"#9bed00","icon":"&#x25ba;"}}, "remote": {"event": {"colour":"#ce0071","icon":"&#x25bc;"},"action":{"colour":"#00a08a","icon":"&#x25c4;"},"eventBinding": {"colour":"#ce0071","icon":"&#x2194;"},"actionBinding":{"colour":"#00a08a","icon":"&#x2194;"}}, "unbound": {"event": {"colour":"#ce0071","icon":"&#x25ac;"},"action":{"colour":"#00a08a","icon":"&#x25ac;"}}};
  if(navigator.issmart){
    $('head').append('<style>.fixed-table-body{overflow-y: hidden;} body{zoom: 140%}</style>');
  };
  // get the node name
  if (window.location.pathname.split( '/' )[1]=="nodes") node = decodeURIComponent(window.location.pathname.split( '/' )[2].replace(/\+/g, '%20'));
  if(node) {
    setEvents();
    updateLogs();
    checkReload();
  }
  // selecct first page
  $('*[data-nav]')[0].click();
  // init scrollable divs
  $('.scrollbar-inner').scrollbar();
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

var setEvents = function(){
  $('body').on('touchend touchcancel',':not(input)', function (e) {
    if(navigator.issmart) $('body').removeClass('touched');
  });
  $('body').on('touchstart',':not(input)', function (e) {
    if(navigator.issmart) $(this).trigger('click');
  });
  $('body').on('input','input[type=range]input[data-action]', function (e){
    var ele = $(this);
    var action = $(ele).data('action');
    var arg = "{'arg':"+stringify($(this).val())+"}";
    if(!_.isFunction($(this).data('throttle'))) {
      $(ele).data('throttle', _.throttle(function(act, ar) {
        callAction(act, ar);
      }, 250));
    }
    $(ele).data('throttle')(action, arg);
  });
  $('body').on('click','*[data-arg], *[data-action], *[data-actionon]*[data-actionoff]', function (e) {
    e.preventDefault();
    if(!$('body').hasClass('touched')) {
      var arg = '';
      var action = '';
      if(navigator.issmart) $('body').addClass('touched');
      if (!_.isUndefined($(this).data('arg-type'))) var type = $(this).data('arg-type')
      else type = false;
      if (!_.isUndefined($(this).data('action-on')) && !_.isUndefined($(this).data('action-off'))) {
        if ($(this).hasClass('active')) action = $(this).data('actionoff');
        else action = $(this).data('actionon');
      }
      else if (!_.isUndefined($(this).data('action'))) action = $(this).data('action');
      else if (!_.isUndefined($(this).parents().data('arg-action'))) action = $(this).parents().data('arg-action');
      if (!_.isUndefined($(this).data('arg-on')) && !_.isUndefined($(this).data('arg-off'))) {
        if ($(this).hasClass('active')) arg = "{'arg':" + stringify($(this).data('arg-off'), type) + "}";
        else arg = "{'arg':" + stringify($(this).data('arg-on'), type) + "}";
      } else {
        if (!_.isUndefined($(this).data('arg'))) arg = "{'arg':" + stringify($(this).data('arg'), type) + "}";
        else if(!_.isUndefined($(this).data('arg-source'))) {
          var val = $($(this).data('arg-source')).data('arg');
          if(_.isUndefined(val)) return false;
          if(!_.isUndefined($(this).data('arg-sourcekey'))) {
            arg = {"arg":{}};
            arg['arg'][$(this).data('arg-sourcekey')] = val;
            if(!_.isUndefined($(this).data('arg-add'))) arg = $.extend(true, arg, {'arg':$(this).data('arg-add')});
            arg = stringify(arg);
          } else arg = "{'arg':"+stringify(val)+"}";
        } else arg = "{}";
      }
      callAction(action, arg);
    }
  });
  $('body').on('click', '*[data-nav]', function (e) {
    $('*[data-nav]').parents('li').removeClass('active');
    $(this).parents('li').addClass('active');
    $("[data-section]").hide();
    $("[data-section="+$(this).data('nav')+"]").show();
  });
};

var callAction = function(action, arg) {
  $.postJSON('http://' + host + '/REST/nodes/' + node + '/actions/' + action + '/call', arg, function () {
    console.log(action + " - Success");
  }).fail(function (e, s) {
    errtxt = s;
    if (e.responseText) errtxt = s + "\n" + e.responseText;
    console.log("exec - Error:\n" + errtxt, "error");
  });
};

var updateLogs = function(){
  if(!("WebSocket" in window)){
    console.log('no websockets');
  }else{
    $.getJSON('http://'+host+'/REST/nodes/' + node, function(data){
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
        var eles = $("[data-event=" + log.alias + "]");
        $.each(eles, function (i, ele) {
          if($.type(log.arg)== "object") log.arg = log.arg[$(ele).data('event-arg')];
          if($(ele).hasClass('dynamic')) {
            $(ele).data('dynamic',log);
          }
          switch ($.type(log.arg)) {
            case "number":
              if ($(ele).is("span")) $(ele).text(log.arg);
              else if ($(ele).not('.meter').is("div")) {
                $(ele).children().filter(function () {
                  return $(this).attr("data-arg") > log.arg;
                }).removeClass('btn-success').addClass('btn-default');
                $(ele).children().filter(function () {
                  return $(this).attr("data-arg") <= log.arg;
                }).removeClass('btn-default').addClass('btn-success');
              } else if ($(ele).is("div.meter")) {
                updatemeter(ele, log.arg);
              } else if($(ele).is("input")) $(ele).not(':active').val(log.arg);
              break;
            case "string":
              if($(ele).hasClass('btn-mswitch')){
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
              } else if ($(ele).hasClass('scrollbar-inner')) {
                var arg = converter.makeHtml(log.arg);
                $(ele).html(arg);
              } else {
                if ($(ele).is("span")) $(ele).text(log.arg);
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
            case "boolean":
              if($(ele).hasClass('btn-switch')){
                if (log.arg) {
                  $(ele).children('[data-arg=true]').removeClass('active').addClass($(ele).data('class-on')).removeClass('btn-default');
                  $(ele).children('[data-arg=false]').addClass('active').addClass('btn-default').removeClass($(ele).data('class-off'));
                } else {
                  $(ele).children('[data-arg=false]').removeClass('active').addClass($(ele).data('class-off')).removeClass('btn-default');
                  $(ele).children('[data-arg=true]').addClass('active').addClass('btn-default').removeClass($(ele).data('class-on'));                  
                }
              }
              break;
          }
        });
        var eles = $("[data-status=" + log.alias + "]");
        $.each(eles, function (i, ele) {
          var ele = $(ele);
          if(!_.isUndefined(log.arg) && !_.isUndefined(log.arg['level']) && _.isNumber(log.arg['level'])){
            var msg = '';
            if(!_.isUndefined(log.arg['message']) && _.isString(log.arg['message'])) msg = log.arg['message'];
            ele.find('.status').not('[data-status]').text(msg);
            if(ele.hasClass('status')) ele.text(msg);
            switch(log.arg['level']) {
              case 0:
                ele.removeClass('label-default label-warning label-danger label-primary').addClass('label-success');
                break;
              case 1:
                ele.removeClass('label-default label-success label-danger label-primary').addClass('label-warning');
                break;
              case 2:
              case 3:
              case 4:
                ele.removeClass('label-default label-success label-warning label-primary').addClass('label-danger');
                break;
              case 5:
                ele.removeClass('label-default label-success label-warning label-danger').addClass('label-primary');
                break;
            }
          }
        });
        var eles = $("[data-render=" + log.alias + "]");
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