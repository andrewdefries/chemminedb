create function ap(text) returns bytea as '/home/ycao/dev/chemmineng/compounddb/support/pgchem.so', 'ap' language c strict;
create function sim(bytea, bytea) returns double precision as '/home/ycao/dev/chemmineng/compounddb/support/pgchem.so', 'sim' language c strict;

