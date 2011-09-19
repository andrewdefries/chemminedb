<?xml version="1.0" encoding="UTF-8"?>
<screen id="${screen.id}" xmlns:py="http://purl.org/kid/ns#">
  <properties>
    <name>${screen.name}</name>
    <description>${screen.description}</description>
    <owner>
      <name>${screen.owner.first_name} ${screen.owner.last_name}</name>
      <institute>${screen.owner.get_profile().institute}</institute>
    </owner>
    <pi>${screen.pi}</pi>
    <coAuthor>${screen.co_author}</coAuthor>
    <funding>
      ${screen.funding}
    </funding>
    <numberOfScreenedCompounds>
      ${screen.number_of_cmp_screened}
    </numberOfScreenedCompounds>
  </properties>
  <strategy>${screen.strategy}</strategy>
  <inactive py:if="inactives">
  	<compound id="${c.id}" py:for="c in inactives">
  	  <identifier>
  	    <library>${c.libname}</library>
  	    <id>${c.cid}</id>
  	    <formula>${c.formula}</formula>
  	  </identifier>
  	 </compound>
  </inactive>
  <screenData>
    <data py:def="datafile(f)">
      <file path="data/${f.fname}"
      type="${f.mime}" id="${f.id}" py:if="hasattr(f, 'fname')"/>
      <publication py:if="isinstance(f, Publication)">
      	<pubmedid>${f.pubmed_id}</pubmedid>
      	<journal>${f.journal}</journal>
      	<volume>${f.volume}</volume>
      	<pages>${f.pages}</pages>
      	<title>${f.pub_title}</title>
      	<author>${f.author}</author>
      	<url py:if="f.publication_url">${f.publication_url}</url>
      	<url py:if="f.web_url">${f.web_url}</url>
      </publication>
      <properties>
        <title py:if="hasattr(f, 'title') and f.title">${f.title}</title>
        <description py:if="hasattr(f, 'description') and f.description">${f.description}</description>
        <reference py:if="hasattr(f, 'reference') and f.reference">data/${f.reference_name}</reference>
        <annotations py:if="hasattr(f, 'extra_annotation') and f.extra_annotation">${f.extra_annotation}</annotations>
      </properties>
    </data>
    <referenceData py:if="reference">
      <data py:replace="datafile(reference)"
        py:if="reference is not None"/>
    </referenceData>
    <data py:replace="datafile(f)" py:for="f in screen_level_files"
      py:if="screen_level_files"/>
  </screenData>
  <compounds>
    <compound id="${c.id}" py:for="c in compounds">
      <identifier>
        <library>${c.libname}</library>
        <id>${c.cid}</id>
        <formula>${c.formula}</formula>
      </identifier>
      <standardAnnotation id="${standardcompoundannotation[c.id].id}"
        py:if="c.id in standardcompoundannotation">
        <properties>
          <title>${standardcompoundannotation[c.id].title}</title>
          <description>${standardcompoundannotation[c.id].description}</description>
          <annotations py:if="standardcompoundannotation[c.id].extra_annotation">${standardcompoundannotation[c.id].extra_annotation}</annotations>
        </properties>
        <assays>
          <assay id="1"
            py:if="standardcompoundannotation[c.id].a1_name">
            <name>${standardcompoundannotation[c.id].a1_name}</name>
            <description>${standardcompoundannotation[c.id].a1_desc}</description>
            <concentration>${standardcompoundannotation[c.id].a1_concentration}</concentration>
            <score>${standardcompoundannotation[c.id].a1_score}</score>
          </assay>
          <assay id="2"
            py:if="standardcompoundannotation[c.id].a2_name">
            <name>${standardcompoundannotation[c.id].a2_name}</name>
            <description>${standardcompoundannotation[c.id].a2_desc}</description>
            <concentration>${standardcompoundannotation[c.id].a2_concentration}</concentration>
            <score>${standardcompoundannotation[c.id].a2_score}</score>
          </assay>
          <assay id="3"
            py:if="standardcompoundannotation[c.id].a3_name">
            <name>${standardcompoundannotation[c.id].a3_name}</name>
            <description>${standardcompoundannotation[c.id].a3_desc}</description>
            <concentration>${standardcompoundannotation[c.id].a3_concentration}</concentration>
            <score>${standardcompoundannotation[c.id].a3_score}</score>
          </assay>
         </assays>
      </standardAnnotation>
      <compoundData>
        <data py:replace="datafile(f)"
          py:for="f in compound_files[c.id]"
          py:strip="True" py:if="compound_files[c.id]"/>
      </compoundData>
    </compound>
  </compounds>
</screen>
