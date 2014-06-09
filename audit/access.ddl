CREATE TABLE accesses (
	server     VARCHAR2(64),
	time       VARCHAR2(64),
	volid      INTEGER,
	host       VARCHAR2(16),
	CONSTRAINT pk_accesses PRIMARY KEY (server, time, volid, host)
);

CREATE INDEX accesses_volid_index ON accesses(volid);
CREATE INDEX accesses_server_index ON accesses(server);
CREATE INDEX accesses_time_index ON accesses(time);
