<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="templates.xsl"/>
  <xsl:output method="html" indent="yes" doctype-system="about:legacy-compat"/>
  <xsl:variable name="allowedSymbols" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'"/>
  <xsl:template match="/">
    <html lang="en" xsl:version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <head>
        <meta charset="utf-8"/>
        <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
        <meta name="apple-mobile-web-app-capable" content="yes"/>
        <meta name="apple-mobile-web-app-status-bar-style" content="black"/>
        <meta name="theme-color" content="#000000"/>
        <!-- The above 3 meta tags *must* come first in the head; any other head content must come *after* these tags -->
        <title></title>
        <!-- Bootstrap -->
        <link href="css/components.css" rel="stylesheet"/>
        <link href="css/main.css" rel="stylesheet"/>
      </head>
      <body>
        <xsl:if test="//footer">
          <xsl:attribute name="class">
            <xsl:text>hasfooter</xsl:text>
          </xsl:attribute>
        </xsl:if>
        <!-- main nav -->
        <nav class="navbar navbar-inverse navbar-fixed-top" data-toggle="collapse" data-target=".nav-collapse">
          <div class="container-fluid">
            <!-- Brand and toggle get grouped for better mobile display -->
            <div class="navbar-header">
              <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#nodel-navbar" aria-expanded="false">
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
              </button>
              <xsl:choose>
              <xsl:when test="/pages/@logo">
                <a class="navbar-brand" href="#"><img src="{/pages/@logo}"/><span id="title"><xsl:value-of select="/pages/@title"/></span></a>
              </xsl:when>
              <xsl:otherwise>
                <a class="navbar-brand" href="#"><img src="img/logo.png"/><span id="title"><xsl:value-of select="/pages/@title"/></span></a>
              </xsl:otherwise>
              </xsl:choose>
            </div>
            <!-- Collect the nav links, forms, and other content for toggling -->
            <div class="collapse navbar-collapse" id="nodel-navbar" role="navigation">
              <ul class="nav navbar-nav">
                <xsl:for-each select="/pages/page|/pages/pagegroup">
                  <xsl:if test="self::pagegroup">
                  <li class="dropdown">
                    <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false"><xsl:value-of select="@title"/><span class="caret"></span></a>
                    <ul class="dropdown-menu">
                      <xsl:for-each select="page">
                        <li>
                          <a href="#" data-nav="{translate(@title,translate(@title,$allowedSymbols,''),'')}" data-toggle="collapse" data-target="#nodel-navbar.in">
                            <xsl:if test="@action">
                              <xsl:attribute name="data-action">
                                <xsl:value-of select="@action"/>
                              </xsl:attribute>
                            </xsl:if>
                            <xsl:value-of select="@title"/>
                          </a>
                        </li>
                      </xsl:for-each>
                    </ul>
                  </li>
                  </xsl:if>
                    <xsl:if test="self::page">
                    <li>
                      <a href="#" data-nav="{translate(@title,translate(@title,$allowedSymbols,''),'')}" data-toggle="collapse" data-target="#nodel-navbar.in">
                        <xsl:if test="@action">
                          <xsl:attribute name="data-action">
                            <xsl:value-of select="@action"/>
                          </xsl:attribute>
                        </xsl:if>
                        <xsl:value-of select="@title"/>
                      </a>
                    </li>
                  </xsl:if>
                </xsl:for-each>
              <!--<xsl:for-each select="/pages/page[not(page)]">
                <li><a href="#" data-nav="{@title}"><xsl:value-of select="@title"/></a></li>
              </xsl:for-each>-->
              </ul>
              <div class="navbar-right">
                <xsl:for-each select="/pages/header/button">
                  <a href="#" data-action="{@action}">
                    <xsl:attribute name="class">
                      <xsl:choose>
                        <xsl:when test="@class">btn navbar-btn <xsl:value-of select="@class"/></xsl:when>
                        <xsl:otherwise>btn btn-default navbar-btn</xsl:otherwise>
                      </xsl:choose>
                    </xsl:attribute>
                    <xsl:value-of select="text()"/>
                    <xsl:apply-templates select="badge|icon"/>
                  </a>
                </xsl:for-each>
                <p class="navbar-text" id="clock"></p>
              </div>
            </div><!-- /.navbar-collapse -->
          </div><!-- /.container-fluid -->
        </nav>
        <!-- end main nav -->
        <!-- offline modal -->
        <div class="modal" id="offline" tabindex="-1" role="dialog" aria-labelledby="offlinelabel" data-backdrop="static" data-keyboard="false" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h4 class="modal-title" id="offlinelabel">Offline</h4>
              </div>
              <div class="modal-body">
                <p>The system is currently offline. Please wait...</p>
              </div>
            </div>
          </div>
        </div>
        <!-- end offline modal -->
        <!-- confirm modal -->
        <div class="modal" id="confirm" tabindex="-1" role="dialog" aria-labelledby="confirmlabel" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&#215;</button>
                <h4 class="modal-title" id="confirmlabel"></h4>
              </div>
              <div class="modal-body">
                <p id="confirmtext"></p>
                <div id="confirmkeypad">
                  <div class="row">
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="1">1</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="2">2</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="3">3</a></div>
                  </div>
                  <div class="row">
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="4">4</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="5">5</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="6">6</a></div>
                  </div>
                  <div class="row">
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="7">7</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="8">8</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="9">9</a></div>
                  </div>
                  <div class="row">
                    <div class="col-xs-4 col-xs-offset-4"><a href="#" class="btn btn-block btn-default" data-keypad="0">0</a></div>
                    <div class="col-xs-4"><a href="#" class="btn btn-block btn-default" data-keypad="-1">&#x232b;</a></div>
                  </div>
                  <div class="row">
                    <div class="col-xs-12">
                      <input id="confirmcodesrc" type="hidden" data-event="ConfirmCode"/>
                      <input id="confirmcode" class="form-control" type="password" readonly="true"/>
                    </div>
                  </div>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
                <button id="confirmaction" class="btn btn-danger btn-ok">Ok</button>
              </div>
            </div>
          </div>
        </div>
        <!-- end offline modal -->
        <!-- pages -->
        <xsl:for-each select="//page">
          <div class="container-fluid page" data-section="{translate(@title,translate(@title,$allowedSymbols,''),'')}">
            <xsl:apply-templates select="row"/>
            <xsl:apply-templates select="*[starts-with(name(), 'special_')]"/>
          </div>
        </xsl:for-each>
        <!-- end pages -->
        <!-- footer -->
        <xsl:if test="//footer">
          <footer class="navbar navbar-default navbar-fixed-bottom">
            <div class="container-fluid">
              <xsl:for-each select="//footer">
                <xsl:apply-templates select="row"/>
              </xsl:for-each>
            </div>
          </footer>
        </xsl:if>
        <!-- end footer -->
        <script src="js/components.js"></script>
        <script src="js/main.js"></script>
        <script id="dynamicSelect" type="text/x-jsrender">
        <![CDATA[
          {{for arg}}
            <li><a href="#" data-arg="{{if key}}{{>key}}{{else}}{{>value}}{{/if}}">{{>value}}</a></li>
          {{/for}}
        ]]>
        </script>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>