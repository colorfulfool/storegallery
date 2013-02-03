drop table if exists users;
create table users (
  id integer primary key autoincrement,
  username string not null unique,
  displayname string,
  password_hash string not null,
  level integer not null,
  picture_url string
);

drop table if exists visitors;
create table visitors (
  id integer primary key autoincrement,
  visits integer not null default(1),
  last_visit datetime
);

drop table if exists posters;
create table posters (
  id integer primary key autoincrement,
  name string,
  info string,
  picrelated_url string,
  visits integer not null default(1),
  last_visit datetime
);

drop table if exists comments;
create table comments (
  id integer primary key autoincrement,
  poster_id integer not null,
  message text,
  object_id int not null,
  object_class string not null,
  in_reply_to int,
  image_url string,
  posted datetime not null,
  foreign key(poster_id) references posters(id),
  foreign key(in_reply_to) references comments(id)
);

drop table if exists pictures;
create table pictures (
  id integer primary key autoincrement,
  image_url string,
  title string,
  description string,
  sent datetime default(datetime('now','localtime')),
  views int default(0)
);

drop table if exists things;
create table things (
  id integer primary key autoincrement,
  content string,
  title string,
  description string,
  sent datetime default(datetime('now','localtime')),
  views int default(0)
);

drop table if exists thumbnails;
create table thumbnails (
  id integer primary key autoincrement,
  image string,
  args string,
  thumbnail string,
  thumbnail_width integer
);