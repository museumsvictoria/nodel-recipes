<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="templates.xsl"/>
  <xsl:output method="html" indent="yes"/>
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
              <a class="navbar-brand" id="title" href="#"><xsl:value-of select="/pages/@title"/></a>
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
                      <li><a href="#" data-nav="{translate(@title,translate(@title,$allowedSymbols,''),'')}"><xsl:value-of select="@title"/></a></li>
                    </xsl:for-each>
                  </ul>
                </li>
                </xsl:if>
                <xsl:if test="self::page">
                <li><a href="#" data-nav="{translate(@title,translate(@title,$allowedSymbols,''),'')}"><xsl:value-of select="@title"/></a></li>
                </xsl:if>
                </xsl:for-each>
              <!--<xsl:for-each select="/pages/page[not(page)]">
                <li><a href="#" data-nav="{@title}"><xsl:value-of select="@title"/></a></li>
              </xsl:for-each>-->
              </ul>
              <p class="navbar-text navbar-right" id="clock"></p>
            </div><!-- /.navbar-collapse -->
          </div><!-- /.container-fluid -->
        </nav>
        <!-- end main nav -->
        <!-- offline modal -->
        <div class="modal" id="offline" tabindex="-1" role="dialog" aria-labelledby="offlinelabel" data-backdrop="static" aria-hidden="true">
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
        <!-- pages -->
        <xsl:for-each select="//page">
          <div class="container-fluid page" data-section="{translate(@title,translate(@title,$allowedSymbols,''),'')}">
          <xsl:apply-templates select="row"/>
          <xsl:apply-templates select="*[starts-with(name(), 'special_')]"/>
          </div>
        </xsl:for-each>
        <!-- end pages -->
        <!-- footer -->
        <!--<footer class="navbar navbar-default navbar-fixed-bottom">
          <div class="container-fluid">
            <h6 style="margin-top: 17px;">For support, please contact Lumicom: (03) 9005 8222</h6>
          </div>
        </footer>-->
        <!-- end footer -->
        <script src="js/components.js"></script>
        <script src="js/main.js"></script>
        <script id="dynamicSelect" type="text/x-jsrender">
        <![CDATA[
          {{for arg}}
            <li><a href="#" data-arg="{{>value}}">{{>value}}</a></li>
          {{/for}}
        ]]>
        </script>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>