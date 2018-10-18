<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <!-- templates -->
  <!-- row -->
  <xsl:template match="row">
    <div>
      <xsl:attribute name="class">
        <xsl:text>row</xsl:text>
        <xsl:if test="@class">
          <xsl:text> </xsl:text>
          <xsl:value-of select="@class"/>
        </xsl:if>
      </xsl:attribute>
      <xsl:apply-templates select="column"/>
    </div>
  </xsl:template>
  <!-- row -->
  <!-- column -->
  <xsl:template match="column[not(@sm|md|xs)]">
    <div>
      <xsl:choose>
        <xsl:when test="@event or @showevent">
          <xsl:attribute name="class">
            <xsl:text>col-sm-12 sect</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="data-showevent">
            <xsl:choose>
              <xsl:when test="@event">
                <xsl:value-of select="@event"/>
              </xsl:when>
              <xsl:otherwise>
                <xsl:value-of select="@showevent"/>
              </xsl:otherwise>
            </xsl:choose>
          </xsl:attribute>
          <xsl:if test="@value or @showvalue">
            <xsl:attribute name="data-showarg">
              <xsl:choose>
                <xsl:when test="@value">
                  <xsl:value-of select="@value"/>
                </xsl:when>
                <xsl:otherwise>
                  <xsl:value-of select="@showvalue"/>
                </xsl:otherwise>
              </xsl:choose>
            </xsl:attribute>
          </xsl:if>
        </xsl:when>
        <xsl:otherwise>
          <xsl:attribute name="class">
            <xsl:text>col-sm-12</xsl:text>
          </xsl:attribute>
        </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates/>
    </div>
  </xsl:template>
  <xsl:template match="column[@sm|@md|@xs]">
    <div>
      <xsl:choose>
        <xsl:when test="@event or @showevent">
          <xsl:attribute name="class">
            <xsl:if test="@xs">
              <xsl:text>col-xs-</xsl:text>
              <xsl:value-of select="@xs"/>
              <xsl:text> </xsl:text>
            </xsl:if>
            <xsl:if test="@sm">
              <xsl:text>col-sm-</xsl:text>
              <xsl:value-of select="@sm"/>
              <xsl:text> </xsl:text>
            </xsl:if>
            <xsl:if test="@md">
              <xsl:text>col-md-</xsl:text>
              <xsl:value-of select="@md"/>
              <xsl:text> </xsl:text>
            </xsl:if>
            <xsl:text> sect</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="data-showevent">
            <xsl:choose>
              <xsl:when test="@event">
                <xsl:value-of select="@event"/>
              </xsl:when>
              <xsl:otherwise>
                <xsl:value-of select="@showevent"/>
              </xsl:otherwise>
            </xsl:choose>
          </xsl:attribute>
          <xsl:if test="@value or @showvalue">
            <xsl:attribute name="data-showarg">
              <xsl:choose>
                <xsl:when test="@value">
                  <xsl:value-of select="@value"/>
                </xsl:when>
                <xsl:otherwise>
                  <xsl:value-of select="@showvalue"/>
                </xsl:otherwise>
              </xsl:choose>
            </xsl:attribute>
          </xsl:if>
        </xsl:when>
        <xsl:otherwise>
          <xsl:attribute name="class">
            <xsl:if test="@xs">
              <xsl:text>col-xs-</xsl:text>
              <xsl:value-of select="@xs"/>
              <xsl:text> </xsl:text>
            </xsl:if>
            <xsl:if test="@sm">
              <xsl:text>col-sm-</xsl:text>
              <xsl:value-of select="@sm"/>
              <xsl:text> </xsl:text>
            </xsl:if>
            <xsl:if test="@md">
              <xsl:text>col-md-</xsl:text>
              <xsl:value-of select="@md"/>
            </xsl:if>
          </xsl:attribute>
        </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates/>
    </div>
  </xsl:template>
  <!-- column -->
  <!-- title -->
  <xsl:template match="title">
    <h4>
      <xsl:if test="@showevent">
        <xsl:attribute name="class">
          <xsl:text>sect</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:if test="@event">
        <xsl:attribute name="data-event">
          <xsl:value-of select="@event"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:value-of select="current()"/>
    </h4>
  </xsl:template>
  <!-- title -->
  <!-- text -->
  <xsl:template match="text">
    <p>
      <xsl:if test="@showevent">
        <xsl:attribute name="class">
          <xsl:text>sect</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:if test="@event">
        <xsl:attribute name="data-event">
          <xsl:value-of select="@event"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:value-of select="current()"/>
    </p>
  </xsl:template>
  <!-- text -->
  <!-- button -->
  <xsl:template match="button[not(@type)]">
    <a href="#" data-action="{@action}" type="button">
      <xsl:if test="(@confirm or @confirmtext)">
        <xsl:attribute name="data-confirm">true</xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtitle">
        <xsl:attribute name="data-confirmtitle">
          <xsl:value-of select="@confirmtitle"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtext">
        <xsl:attribute name="data-confirmtext">
          <xsl:value-of select="@confirmtext"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:attribute name="class">
        <xsl:choose>
          <xsl:when test="@class">btn <xsl:value-of select="@class"/></xsl:when>
          <xsl:otherwise>btn btn-default</xsl:otherwise>
        </xsl:choose>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
        <xsl:if test="badge">
          <xsl:text> haschild</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@event">
        <xsl:attribute name="data-event">
          <xsl:value-of select="@event"/>
        </xsl:attribute>
        <xsl:attribute name="data-class-on">
          <xsl:choose>
            <xsl:when test="@class-on"><xsl:value-of select="@class-on"/></xsl:when>
            <xsl:otherwise>btn-primary</xsl:otherwise>
          </xsl:choose>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:value-of select="text()"/>
      <xsl:apply-templates select="badge|icon|text|image"/>
    </a>
  </xsl:template>
  <xsl:template match="button[@type]">
    <xsl:if test="@type='momentary'">
      <a href="#" data-actionon="{@action-on}" data-actionoff="{@action-off}" type="button">
        <xsl:if test="(@confirm or @confirmtext)">
          <xsl:attribute name="data-confirm">true</xsl:attribute>
        </xsl:if>
        <xsl:if test="@confirmtitle">
          <xsl:attribute name="data-confirmtitle">
            <xsl:value-of select="@confirmtitle"/>
          </xsl:attribute>
        </xsl:if>
        <xsl:if test="@confirmtext">
          <xsl:attribute name="data-confirmtext">
            <xsl:value-of select="@confirmtext"/>
          </xsl:attribute>
        </xsl:if>
        <xsl:attribute name="class">
          <xsl:choose>
            <xsl:when test="@class">btn <xsl:value-of select="@class"/></xsl:when>
            <xsl:otherwise>btn btn-default</xsl:otherwise>
          </xsl:choose>
        </xsl:attribute>
        <xsl:value-of select="text()"/>
        <xsl:apply-templates select="badge|icon|text|image"/>
      </a>
    </xsl:if>
  </xsl:template>
  <!-- button -->
  <!-- buttongroup -->
  <xsl:template match="buttongroup">
    <div role="group">
      <xsl:attribute name="class">
        <xsl:if test="not(@type)">
          <xsl:choose>
            <xsl:when test="@class">btn-group <xsl:value-of select="@class"/></xsl:when>
            <xsl:otherwise>btn-group</xsl:otherwise>
          </xsl:choose>
        </xsl:if>
        <xsl:if test="@type='vertical'">
          <xsl:choose>
            <xsl:when test="@class">btn-group-vertical btn-block <xsl:value-of select="@class"/></xsl:when>
            <xsl:otherwise>btn-group-vertical btn-block</xsl:otherwise>
          </xsl:choose>
        </xsl:if>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:apply-templates select="button"/>
    </div>
  </xsl:template>
  <!-- buttongroup -->
  <!-- icon -->
  <xsl:template match="icon">
    <span class="glyphicon glyphicon-{@type}"></span>
  </xsl:template>
  <!-- icon -->
  <!-- image -->
  <xsl:template match="image">
    <img src="{@source}"></img>
  </xsl:template>
  <!-- image -->
  <!-- grid -->
  <xsl:template match="grid">
    <table class="btn-grid">
      <xsl:for-each select="row">
        <tr>
          <xsl:for-each select="cell">
            <td>
              <xsl:apply-templates />
            </td>
          </xsl:for-each>
        </tr>
      </xsl:for-each>
    </table>
  </xsl:template>
  <!-- grid -->
  <!-- switch -->
  <xsl:template match="switch">
    <div role="group" data-event="{@event}" data-arg-action="{@action}">
      <xsl:if test="(@confirm or @confirmtext)">
        <xsl:attribute name="data-confirm">true</xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtitle">
        <xsl:attribute name="data-confirmtitle">
          <xsl:value-of select="@confirmtitle"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtext">
        <xsl:attribute name="data-confirmtext">
          <xsl:value-of select="@confirmtext"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:attribute name="class">
        <xsl:text>btn-group btn-switch</xsl:text>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:attribute name="data-class-off">
        <xsl:choose>
          <xsl:when test="@class-off"><xsl:value-of select="@class-off"/></xsl:when>
          <xsl:otherwise>btn-danger</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:attribute name="data-class-on">
        <xsl:choose>
          <xsl:when test="@class-on"><xsl:value-of select="@class-on"/></xsl:when>
          <xsl:otherwise>btn-success</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <a href="#" class="btn btn-default" data-arg="false">
        <xsl:choose>
          <xsl:when test="@off"><xsl:value-of select="@off"/></xsl:when>
          <xsl:otherwise>Off</xsl:otherwise>
        </xsl:choose>
      </a>
      <a href="#" class="btn btn-default" data-arg="true">
         <xsl:choose>
          <xsl:when test="@on"><xsl:value-of select="@on"/></xsl:when>
          <xsl:otherwise>On</xsl:otherwise>
        </xsl:choose>
      </a>
    </div>
  </xsl:template>
  <!-- switch -->
  <!-- partialswitch -->
  <xsl:template match="partialswitch">
    <div role="group" data-event="{@event}" data-arg-action="{@action}">
      <xsl:if test="(@confirm or @confirmtext)">
        <xsl:attribute name="data-confirm">true</xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtitle">
        <xsl:attribute name="data-confirmtitle">
          <xsl:value-of select="@confirmtitle"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtext">
        <xsl:attribute name="data-confirmtext">
          <xsl:value-of select="@confirmtext"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:attribute name="class">
        <xsl:text>btn-group btn-pswitch</xsl:text>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:attribute name="data-class-off">
        <xsl:choose>
          <xsl:when test="@class-off"><xsl:value-of select="@class-off"/></xsl:when>
          <xsl:otherwise>btn-danger</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:attribute name="data-class-on">
        <xsl:choose>
          <xsl:when test="@class-on"><xsl:value-of select="@class-on"/></xsl:when>
          <xsl:otherwise>btn-success</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <a href="#" class="btn btn-default" data-arg="Off">
        <xsl:choose>
          <xsl:when test="@off"><xsl:value-of select="@off"/></xsl:when>
          <xsl:otherwise>Off</xsl:otherwise>
        </xsl:choose>
      </a>
      <a href="#" class="btn btn-default" data-arg="On">
         <xsl:choose>
          <xsl:when test="@on"><xsl:value-of select="@on"/></xsl:when>
          <xsl:otherwise>On</xsl:otherwise>
        </xsl:choose>
      </a>
    </div>
  </xsl:template>
  <!-- partialswitch -->
  <!-- pills -->
  <xsl:template match="pills">
    <ul data-event="{@event}" data-arg-action="{@action}">
      <xsl:if test="(@confirm or @confirmtext)">
        <xsl:attribute name="data-confirm">true</xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtitle">
        <xsl:attribute name="data-confirmtitle">
          <xsl:value-of select="@confirmtitle"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@confirmtext">
        <xsl:attribute name="data-confirmtext">
          <xsl:value-of select="@confirmtext"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:attribute name="class">
        <xsl:text>nav nav-pills nav-stacked</xsl:text>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:for-each select="pill">
        <li>
          <xsl:if test="badge or @showevent">
            <xsl:attribute name="class">
              <xsl:choose>
                <xsl:when test="badge and @showevent">
                  <xsl:text>haschild sect</xsl:text>
                </xsl:when>
                <xsl:when test="badge and not(@showevent)">
                  <xsl:text>haschild</xsl:text>
                </xsl:when>
                <xsl:when test="@showevent and not(badge)">
                  <xsl:text>sect</xsl:text>
                </xsl:when>
              </xsl:choose>
            </xsl:attribute>
          </xsl:if>
          <xsl:if test="@showevent">
            <xsl:attribute name="class">
              <xsl:text>sect</xsl:text>
            </xsl:attribute>
            <xsl:attribute name="data-showevent">
              <xsl:value-of select="@showevent"/>
            </xsl:attribute>
            <xsl:if test="@showvalue">
              <xsl:attribute name="data-showarg">
                <xsl:value-of select="@showvalue"/>
              </xsl:attribute>
            </xsl:if>
          </xsl:if>
          <a href="#" data-arg="{@value}"><xsl:value-of select="text()"/><xsl:apply-templates select="badge"/></a>
        </li>
      </xsl:for-each>
    </ul>
  </xsl:template>
  <!-- pills -->
  <!-- select -->
  <xsl:template match="select">
    <div>
      <xsl:attribute name="class">
        <xsl:text>btn-group btn-select</xsl:text>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <button type="button" class="btn {@class} dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
        <span>&#160;</span>&#160;<span class="caret"></span>
      </button>
      <ul class="dropdown-menu" data-event="{@event}" data-arg-action="{@action}">
        <xsl:if test="(@confirm or @confirmtext)">
          <xsl:attribute name="data-confirm">true</xsl:attribute>
        </xsl:if>
        <xsl:if test="@confirmtitle">
          <xsl:attribute name="data-confirmtitle">
            <xsl:value-of select="@confirmtitle"/>
          </xsl:attribute>
        </xsl:if>
        <xsl:if test="@confirmtext">
          <xsl:attribute name="data-confirmtext">
            <xsl:value-of select="@confirmtext"/>
          </xsl:attribute>
        </xsl:if>
        <xsl:for-each select="item">
          <li>
            <xsl:if test="@showevent">
              <xsl:attribute name="class">
                <xsl:text>sect</xsl:text>
              </xsl:attribute>
              <xsl:attribute name="data-showevent">
                <xsl:value-of select="@showevent"/>
              </xsl:attribute>
              <xsl:if test="@showvalue">
                <xsl:attribute name="data-showarg">
                  <xsl:value-of select="@showvalue"/>
                </xsl:attribute>
              </xsl:if>
            </xsl:if>
            <a href="#" data-arg="{@value}"><xsl:value-of select="text()"/></a>
          </li>
        </xsl:for-each>
      </ul>
    </div>
  </xsl:template>
  <!-- select -->
  <!-- dynamicselect -->
  <xsl:template match="dynamicselect">
    <div class="btn-group btn-select">
      <button type="button" class="btn {@class} dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
        <span>&#160;</span>&#160;<span class="caret"></span>
      </button>
      <ul class="dropdown-menu dynamic" data-event="{@event}" data-arg-action="{@action}" data-render="{@data}" data-render-template="#dynamicSelect">
        <xsl:if test="(@confirm or @confirmtext)">
          <xsl:attribute name="data-confirm">true</xsl:attribute>
        </xsl:if>
        <xsl:if test="@confirmtitle">
          <xsl:attribute name="data-confirmtitle">
            <xsl:value-of select="@confirmtitle"/>
          </xsl:attribute>
        </xsl:if>
        <xsl:if test="@confirmtext">
          <xsl:attribute name="data-confirmtext">
            <xsl:value-of select="@confirmtext"/>
          </xsl:attribute>
        </xsl:if>
      </ul>
    </div>
  </xsl:template>
  <!-- select -->
  <!-- status -->
  <xsl:template match="status">
    <div data-status="{@event}">
      <xsl:attribute name="class">
        <xsl:text>alert alert-mini label-default</xsl:text>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:if test="@page">
        <xsl:attribute name="data-nav">
          <xsl:value-of select="translate(@page,translate(@page,$allowedSymbols,''),'')"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:apply-templates select="link"/><xsl:apply-templates select="swich|partialswitch"/><xsl:apply-templates select="badge|partialbadge"/><strong><xsl:value-of select="text()"/></strong><br/><span class="status">Unknown</span>
    </div>
  </xsl:template>
  <!-- status -->
  <!-- badge -->
  <xsl:template match="badge">
    <span data-status="{@event}">
      <xsl:attribute name="class">
        <xsl:choose>
          <xsl:when test="@type">
            <xsl:text>label label-default status </xsl:text>
            <xsl:value-of select="@type"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:text>label label-default status</xsl:text>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:value-of select="text()"/>
    </span>
  </xsl:template>
  <!-- badge -->
  <!-- partialbadge -->
  <xsl:template match="partialbadge">
    <span class="label label-default label-pbadge" data-event="{@event}" data-class-off="label-danger" data-class-on="label-success">
    <xsl:attribute name="data-off">
      <xsl:choose>
        <xsl:when test="@off"><xsl:value-of select="@off"/></xsl:when>
        <xsl:otherwise>Off</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
    <xsl:attribute name="data-on">
      <xsl:choose>
        <xsl:when test="@on"><xsl:value-of select="@on"/></xsl:when>
        <xsl:otherwise>On</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
    <xsl:value-of select="text()"/>
    </span>
  </xsl:template>
  <!-- partialbadge -->
  <!-- link -->
  <xsl:template match="link[@node and not(@url)]">
    <a href="#" class="btn btn-outline" data-link-node="{@node}"><span class="glyphicon glyphicon-new-window"></span><span><xsl:value-of select="text()"/></span></a>
  </xsl:template>
  <xsl:template match="link[@url and not(@node)]">
    <a href="#" class="btn btn-outline" data-link-url="{@url}"><span class="glyphicon glyphicon-new-window"></span><span><xsl:value-of select="text()"/></span></a>
  </xsl:template>
  <xsl:template match="link[not(@url) and not(@node)]">
    <a href="#" class="btn btn-outline" data-link-event="{../@event}"><span class="glyphicon glyphicon-new-window"></span><span><xsl:value-of select="text()"/></span></a>
  </xsl:template>
  <!-- link -->
  <!-- panel -->
  <xsl:template match="panel">
    <div class="panel panel-default">
      <div class="panel-body">
        <div data-event="{@event}" class="panel{@height}px scrollbar-inner"></div>
      </div>
    </div>
    <style>.panel<xsl:value-of select="@height"/>px {height: <xsl:value-of select="@height"/>px; overflow: hidden;}</style>
  </xsl:template>
  <!-- panel -->
  <!-- range -->
  <xsl:template match="range">
    <div>
      <xsl:attribute name="class">
        <xsl:text>range</xsl:text>
        <xsl:if test="@showevent">
          <xsl:text> sect</xsl:text>
        </xsl:if>
      </xsl:attribute>
      <xsl:if test="@showevent">
        <xsl:attribute name="data-showevent">
          <xsl:value-of select="@showevent"/>
        </xsl:attribute>
        <xsl:if test="@showvalue">
          <xsl:attribute name="data-showarg">
            <xsl:value-of select="@showvalue"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:if>
      <xsl:attribute name="data-type">
        <xsl:value-of select="@type"/>
      </xsl:attribute>
      <xsl:if test="@type='vertical'">
        <xsl:attribute name="class">
          <xsl:text>range rangeh</xsl:text>
          <xsl:choose>
            <xsl:when test="@height"><xsl:value-of select="@height"/></xsl:when>
            <xsl:otherwise>200</xsl:otherwise>
          </xsl:choose>
          <xsl:text>px</xsl:text>
        </xsl:attribute>
        <style>.rangeh<xsl:choose>
          <xsl:when test="@height"><xsl:value-of select="@height"/></xsl:when>
            <xsl:otherwise>200</xsl:otherwise>
          </xsl:choose>px {height: <xsl:choose>
            <xsl:when test="@height"><xsl:value-of select="@height"/></xsl:when>
            <xsl:otherwise>200</xsl:otherwise>
          </xsl:choose>px;}</style>
      </xsl:if>
      <div>
        <xsl:if test="@type='vertical'">
          <xsl:attribute name="class">
            <xsl:text>rangew</xsl:text>
            <xsl:choose>
              <xsl:when test="@height"><xsl:value-of select="@height"/></xsl:when>
              <xsl:otherwise>200</xsl:otherwise>
            </xsl:choose>
            <xsl:text>px</xsl:text>
          </xsl:attribute>
          <style>.rangew<xsl:choose>
            <xsl:when test="@height"><xsl:value-of select="@height"/></xsl:when>
              <xsl:otherwise>200</xsl:otherwise>
            </xsl:choose>px {width: <xsl:choose>
              <xsl:when test="@height"><xsl:value-of select="@height"/></xsl:when>
              <xsl:otherwise>200</xsl:otherwise>
            </xsl:choose>px;}</style>
        </xsl:if>
        <form>
          <input data-arg-source="this" data-action="{@action}" data-event="{@event}" type="range" min="{@min}" max="{@max}" step="1" />
          <output data-event="{@event}"></output>
          <xsl:if test="@type='mute'">
            <a href="#" class="btn btn-default" data-arg-on="true" data-arg-off="false">
              <xsl:attribute name="data-action">
                <xsl:value-of select="@action"/>
                <xsl:text>Muting</xsl:text>
              </xsl:attribute>
              <xsl:attribute name="data-event">
                <xsl:value-of select="@event"/>
                <xsl:text>Muting</xsl:text>
              </xsl:attribute>
              <xsl:attribute name="data-class-on">
                <xsl:choose>
                  <xsl:when test="@class-on">btn <xsl:value-of select="@class-on"/></xsl:when>
                  <xsl:otherwise>btn-danger</xsl:otherwise>
                </xsl:choose>
              </xsl:attribute>
              <xsl:text>Mute</xsl:text>
              <xsl:apply-templates select="badge|icon"/>
            </a>
          </xsl:if>
        </form>
      </div>
    </div>
  </xsl:template>
  <!-- range -->
  <!-- field -->
  <xsl:template match="field">
    <div><form><input class="form-control" data-arg-source="this" data-event="{@event}" readonly="true"/></form></div>
  </xsl:template>
  <!-- field -->
  <!-- meter -->
  <xsl:template match="meter">
    <div class="meter" data-event="{@event}">
      <xsl:attribute name="data-type">
        <xsl:value-of select="@type"/>
      </xsl:attribute>
      <xsl:attribute name="data-range">
        <xsl:choose>
          <xsl:when test="@range"><xsl:value-of select="@range"/></xsl:when>
          <xsl:otherwise>perc</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <div>
        <div data-toggle="tooltip" class="base label-default"></div>
        <div class="bar">
          <div class="label-danger"></div>
          <div class="label-warning"></div>
          <div class="label-success"></div>
        </div>
      </div>
      <p>0</p>
    </div>
  </xsl:template>
  <!-- meter -->
  <!-- gap -->
  <xsl:template match="gap">
    <div>
      <xsl:attribute name="style">
        <xsl:choose>
          <xsl:when test="@value">min-height:<xsl:value-of select="@value"/>px;</xsl:when>
          <xsl:otherwise>min-height:20px;</xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </div>
  </xsl:template>
  <!-- gap -->
</xsl:stylesheet>