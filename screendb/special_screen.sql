CREATE TABLE "screendb_dtsentry" (
    "id" serial NOT NULL PRIMARY KEY,
    "compound_id" integer REFERENCES "compounddb_compound" ("id") DEFERRABLE INITIALLY DEFERRED,
    "plate" varchar(16) NOT NULL,
    "well" varchar(16) NOT NULL,
    "control" varchar(1) NOT NULL
)
;
create index screendb_dtsentry_cid on screendb_dtsentry (plate);
create index screendb_dtsentry_plate on screendb_dtsentry (plate);

CREATE TABLE "screendb_dts249entry" (
    "dtsentry_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "screendb_dtsentry" ("id") DEFERRABLE INITIALLY DEFERRED,
    "raw" numeric(10, 2) NOT NULL,
    "score" numeric(10, 2) NOT NULL,
    "comment" varchar(256) NOT NULL,
    "plate_z1" numeric(10, 2) NOT NULL,
    "plate_z" numeric(10, 2) NOT NULL,
    "sample_mean" numeric(10, 2) NOT NULL,
    "sample_SD" numeric(10, 2) NOT NULL
)
;
CREATE TABLE "screendb_dts251entry" (
    "dtsentry_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "screendb_dtsentry" ("id") DEFERRABLE INITIALLY DEFERRED,
	"raw" numeric(10, 2) NOT NULL,
	"score" numeric(10, 2) NOT NULL,
	"stdev" numeric(10, 2) NOT NULL
)
;
