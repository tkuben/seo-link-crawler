CREATE TABLE `all_links` (
  `url` varchar(255) DEFAULT NULL,
  `depth` smallint(6) DEFAULT NULL,
  `root` varchar(55) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


CREATE TABLE `non_working_urls` (
  `url` varchar(255) DEFAULT NULL,
  `depth` smallint(6) DEFAULT NULL,
  `error` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE `to_be_crawled_links` (
  `url` varchar(255) DEFAULT NULL,
  `depth` smallint(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1; 