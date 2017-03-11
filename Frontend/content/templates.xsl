<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <!-- templates -->
  <!-- row -->
  <xsl:template match="row">
    <div class="row {@class}">
    <xsl:apply-templates select="column"/>
    </div>
  </xsl:template>
  <!-- row -->
  <!-- column -->
  <xsl:template match="column[not(@sm|md)]">
    <div class="col-sm-12">
      <xsl:apply-templates/>
    </div>
  </xsl:template>
  <xsl:template match="column[@sm and not(@md)]">
    <div class="col-sm-{@sm}">
      <xsl:apply-templates/>
    </div>
  </xsl:template>
  <xsl:template match="column[@md and not(@sm)]">
    <div class="col-md-{@md}">
      <xsl:apply-templates/>
    </div>
  </xsl:template>
  <xsl:template match="column[@md and @sm]">
    <div class="col-md-{@md} col-sm-{@sm}">
      <xsl:apply-templates/>
    </div>
  </xsl:template>
  <!-- column -->
  <!-- title -->
  <xsl:template match="title">
    <h4><xsl:value-of select="current()"/></h4>
  </xsl:template>
  <!-- title -->
  <!-- button -->
  <xsl:template match="button">
    <a href="#" class="btn {@class}" data-action="{@action}"><xsl:value-of select="text()"/><xsl:apply-templates select="badge"/></a>
  </xsl:template>
  <!-- button -->
  <!-- buttongroup -->
  <xsl:template match="buttongroup">
    <xsl:if test="not(@type)">
    <div class="btn-group {@class}" role="group">
    <xsl:for-each select="button">
      <a href="#" class="btn {@class}" data-action="{@action}"><xsl:value-of select="text()"/><xsl:apply-templates select="badge"/></a>
    </xsl:for-each>
    </div>
    </xsl:if>
    <xsl:if test="@type='vertical'">
    <div class="btn-group-vertical btn-block {@class}" role="group">
    <xsl:for-each select="button">
      <a href="#" class="btn {@class}" data-action="{@action}"><xsl:value-of select="text()"/><xsl:apply-templates select="badge"/></a>
    </xsl:for-each>
    </div>
    </xsl:if>
  </xsl:template>
  <!-- buttongroup -->
  <!-- switch -->
  <xsl:template match="switch">
    <div class="btn-group btn-switch" role="group" data-event="{@event}" data-arg-action="{@action}" data-class-off="btn-danger" data-class-on="btn-success">
      <a href="#" class="btn btn-default" data-arg="false">
        <xsl:choose>
          <xsl:when test="off"><xsl:value-of select="off"/></xsl:when>
          <xsl:otherwise>Off</xsl:otherwise>
        </xsl:choose>
      </a>
      <a href="#" class="btn btn-default" data-arg="true">
         <xsl:choose>
          <xsl:when test="on"><xsl:value-of select="on"/></xsl:when>
          <xsl:otherwise>On</xsl:otherwise>
        </xsl:choose>
      </a>
    </div>
  </xsl:template>
  <!-- switch -->
  <!-- partialswitch -->
  <xsl:template match="partialswitch">
    <div class="btn-group btn-pswitch" role="group" data-event="{@event}" data-arg-action="{@action}" data-class-off="btn-danger" data-class-on="btn-success">
      <a href="#" class="btn btn-default" data-arg="Off">
        <xsl:choose>
          <xsl:when test="off"><xsl:value-of select="off"/></xsl:when>
          <xsl:otherwise>Off</xsl:otherwise>
        </xsl:choose>
      </a>
      <a href="#" class="btn btn-default" data-arg="On">
         <xsl:choose>
          <xsl:when test="on"><xsl:value-of select="on"/></xsl:when>
          <xsl:otherwise>On</xsl:otherwise>
        </xsl:choose>
      </a>
    </div>
  </xsl:template>
  <!-- partialswitch -->
  <!-- pills -->
  <xsl:template match="pills">
    <ul class="nav nav-pills nav-stacked" data-event="{@event}" data-arg-action="{@action}">
    <xsl:for-each select="pill">
      <li><a href="#" data-arg="{@value}"><xsl:value-of select="text()"/><xsl:apply-templates select="badge"/></a></li>
    </xsl:for-each>
    </ul>
  </xsl:template>
  <!-- pills -->
  <!-- select -->
  <xsl:template match="select">
    <div class="btn-group btn-select">
      <button type="button" class="btn {@class} dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
        <span>&#160;</span>&#160;<span class="caret"></span>
      </button>
      <ul class="dropdown-menu" data-event="{@event}" data-arg-action="{@action}">
      <xsl:for-each select="item">
        <li><a href="#" data-arg="{@value}"><xsl:value-of select="text()"/></a></li>
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
      </ul>
    </div>
  </xsl:template>
  <!-- select -->
  <!-- status -->
  <xsl:template match="status">
    <div class="alert alert-mini label-default" data-status="{@event}">
    <xsl:if test="@page">
      <xsl:attribute name="data-nav">
        <xsl:value-of select="translate(@page,translate(@page,$allowedSymbols,''),'')"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:apply-templates select="swich|partialswitch"/><xsl:apply-templates select="badge|partialbadge"/><strong><xsl:value-of select="text()"/></strong><br/><span class="status">Unknown</span>
    </div>
  </xsl:template>
  <!-- status -->
  <!-- badge -->
  <xsl:template match="badge">
    <span class="label label-default status" data-status="{@event}"><xsl:value-of select="text()"/></span>
  </xsl:template>
  <!-- badge -->
  <!-- partialbadge -->
  <xsl:template match="partialbadge">
    <span class="label label-default label-pbadge" data-event="{@event}" data-class-off="label-danger" data-class-on="label-success">
    <xsl:value-of select="text()"/>
    <xsl:attribute name="data-off">
      <xsl:choose>
        <xsl:when test="off"><xsl:value-of select="off"/></xsl:when>
        <xsl:otherwise>Off</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
    <xsl:attribute name="data-on">
      <xsl:choose>
        <xsl:when test="on"><xsl:value-of select="on"/></xsl:when>
        <xsl:otherwise>On</xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
    </span>
  </xsl:template>
  <!-- partialbadge -->
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
    <div><form><input data-arg-source="this" data-action="{@action}" data-event="{@event}" type="range" min="{@min}" max="{@max}" step="1" /></form></div>
  </xsl:template>
  <!-- range -->
  <!-- meter -->
  <xsl:template match="meter">
    <div class="meter" data-event="{@event}">
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
</xsl:stylesheet>