CREATE CONSTRAINT research_key
FOR (research:Research) REQUIRE (research.uuid) IS NODE KEY;

CREATE CONSTRAINT research_arxivId_unique
FOR (research:Research) REQUIRE (research.arxivId) IS UNIQUE;

CREATE CONSTRAINT abstract_key
FOR (abstract:Abstract) REQUIRE (abstract.uuid) IS NODE KEY;

CREATE CONSTRAINT fulltext_key
FOR (fulltext:Fulltext) REQUIRE (fulltext.uuid) IS NODE KEY;

CREATE CONSTRAINT researcher_key
FOR (researcher:Researcher) REQUIRE (researcher.uuid) IS NODE KEY;

CREATE CONSTRAINT arxivset_key
FOR (arxivset:ArxivSet) REQUIRE (arxivset.uuid, arxivset.name) IS NODE KEY;

CREATE CONSTRAINT arxivcategory_key
FOR (arxivcategory:ArxivCategory) REQUIRE (arxivcategory.uuid, arxivcategory.name) IS NODE KEY;

CREATE CONSTRAINT dataoperation_key
FOR (dataoperation:DataOperation) REQUIRE (dataoperation.uuid) IS NODE KEY;

CREATE CONSTRAINT datasource_key
FOR (datasource:DataSource) REQUIRE (datasource.uuid) IS NODE KEY;

CREATE CONSTRAINT datasource_name_unique
FOR (datasource:DataSource) REQUIRE (datasource.name) IS UNIQUE;

CREATE CONSTRAINT method_key
FOR (method:Method) REQUIRE (method.uuid, method.name, method.version) IS NODE KEY;

CREATE CONSTRAINT data_key
FOR (data:Data) REQUIRE (data.uuid) IS NODE KEY;