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
  var eles = $("[data-event]");
  $.each(eles, function () {
    $(this).attr('data-event', $(this).data('event').replace(unicodematch,''));
  });
  var eles = $("[data-status]");
  $.each(eles, function () {
    $(this).attr('data-status', $(this).data('status').replace(unicodematch,''));
  });
  var eles = $("[data-render]");
  $.each(eles, function () {
    $(this).attr('data-render', $(this).data('render').replace(unicodematch,''));
  });
}

var setEvents = function(){
  $(window).resize(function () {
    updatepadding();
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
      if(data.action) callAction(data.action, data.arg);
    }
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
};

var getAction = function(ele){
  var arg = '';
  var action = '';
  if (!_.isUndefined($(ele).data('arg-type'))) var type = $(ele).data('arg-type')
  else type = false;
  if (!_.isUndefined($(ele).data('actionon')) && !_.isUndefined($(ele).data('actionoff'))) {
    if ($(ele).hasClass('active')) action = $(ele).data('actionoff');
    else action = $(ele).data('actionon');
  }
  else if (!_.isUndefined($(ele).data('action'))) action = $(ele).data('action');
  else if (!_.isUndefined($(ele).closest('[data-arg-action]').data('arg-action'))) action = $(ele).closest('[data-arg-action]').data('arg-action');
  if (!_.isUndefined($(ele).data('arg-on')) && !_.isUndefined($(ele).data('arg-off'))) {
    if ($(ele).hasClass('active')) arg = "{'arg':" + stringify($(ele).data('arg-off'), type) + "}";
    else arg = "{'arg':" + stringify($(ele).data('arg-on'), type) + "}";
  } else {
    if (!_.isUndefined($(ele).data('arg'))) arg = "{'arg':" + stringify($(ele).data('arg'), type) + "}";
    else if(!_.isUndefined($(ele).data('arg-source'))) {
      if($(ele).data('arg-source') == 'this') val = $(ele).val();
      else val = $($(ele).data('arg-source')).data('arg');
      if(_.isUndefined(val)) val = {};
      if(!_.isUndefined($(ele).data('arg-sourcekey'))) {
        arg = {"arg":{}};
        arg['arg'][$(ele).data('arg-sourcekey')] = val;
        if(!_.isUndefined($(ele).data('arg-add'))) arg = $.extend(true, arg, {'arg':$(ele).data('arg-add')});
        arg = stringify(arg);
      } else arg = "{'arg':"+stringify(val)+"}";
    } else arg = "{}";
  }
  return {'action': action, 'arg': arg};
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
        var eles = $("[data-showevent='"+log.alias+"']");
        $.each(eles, function (i, ele) {
          if($.type(log.arg)== "object") log.arg = log.arg[$(ele).data('event-arg')];
          if($(ele).hasClass('dynamic')) {
            $(ele).data('dynamic',log);
          }
          switch ($.type(log.arg)) {
            case "string":
              if ($(ele).hasClass('sect')) {
                $(".sect[data-showevent='"+log.alias+"']").hide();
                $(".sect[data-showevent='"+log.alias+"']").filter(function() {
                  return $.inArray(log.arg, $.isArray($(this).data('showarg')) ? $(this).data('showarg') : [$(this).data('showarg')]) >= 0;
                }).show();
              };
              break;
            case "boolean":
              if ($(ele).hasClass('sect')) {
                if (log.arg) $(".sect[data-showevent='"+log.alias+"']").show();
                else $(".sect[data-showevent='"+log.alias+"']").hide();
              };
              break;
          };
        });
        // handle event data updates
        var eles = $("[data-event='"+log.alias+"']");
        $.each(eles, function (i, ele) {
          if($.type(log.arg)== "object") log.arg = log.arg[$(ele).data('event-arg')];
          if($(ele).hasClass('dynamic')) {
            $(ele).data('dynamic',log);
          }
          switch ($.type(log.arg)) {
            case "number":
              if ($(ele).not('.meter').is("div")) {
                $(ele).children().filter(function () {
                  return $(this).attr("data-arg") > log.arg;
                }).removeClass('btn-success').addClass('btn-default');
                $(ele).children().filter(function () {
                  return $(this).attr("data-arg") <= log.arg;
                }).removeClass('btn-default').addClass('btn-success');
              } else if ($(ele).is("div.meter")) {
                updatemeter(ele, log.arg);
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
          }
        });
        var eles = $("[data-status='"+log.alias+"']");
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
          } else if(_.isBoolean(log.arg)) {
            if (log.arg) $(ele).addClass('label-success').removeClass('label-default');
            else $(ele).addClass('label-default').removeClass('label-success');
          }
        });
        var eles = $("[data-render='"+log.alias+"']");
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