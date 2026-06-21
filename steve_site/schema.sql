-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS user_modify_tmp;
DROP TABLE IF EXISTS blog;
DROP TABLE IF EXISTS image;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  level TEXT NOT NULL
);

CREATE TABLE user_modify_tmp (
  id INTEGER NOT NULL,
  reset_pwd_token TEXT NOT NULL,
  reset_pwd_expire_time TIMESTAMP NOT NULL,
  FOREIGN KEY (id) REFERENCES user (id)
);

CREATE TABLE blog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  edited TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  pv INTEGER DEFAULT 0,
  deleted_at TIMESTAMP DEFAULT NULL,
  status TEXT DEFAULT 'PUBLIC',
  cover_url TEXT DEFAULT NULL,
  FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE image (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL,
    image_cnt INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    file_size INTEGER NOT NULL,  -- BYTES
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'NORMAL',
    url_and_size JSON NOT NULL,  -- {'thumb': {'url': 'http://r2.com/1.jpg', 'width': 200, 'height': 150, 'size': 7203}}
    FOREIGN KEY (user_id) REFERENCES user(id)
);
CREATE INDEX idx_image_user_id ON image(user_id);
