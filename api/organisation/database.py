import sqlalchemy as dba
from sqlalchemy import desc
import logging


# create a logger instance
logger = logging.getLogger(__name__)


def fetch_user_id_from_discord_id(discord_id, engine):
    try:
        metadata = dba.MetaData()
        user = dba.Table("user", metadata, autoload_with=engine)
        s = dba.select((user.c.id)).where(user.c.discord_id == discord_id)
        conn = engine.connect()
        user_id = conn.execute(s).scalar()
        return user_id
    except Exception as e:
        logger.exception(e)
        return e


class Database:
    def __init__(self, database, host, user, password):
        self.database = database
        self.db_host = host
        self.db_user = user
        self.db_pass = password


    def get_college_rank(self):
        """function to define college rank"""
        try:
            engine = dba.create_engine(
                "mysql+pymysql://%s:%s@%s/%s"
                % (self.db_user, self.db_pass, self.db_host, self.database),
                echo=False,
                )
            query = "SELECT o.title, SUM(tk.karma), COUNT(tk.id) FROM organization o " \
                    "INNER JOIN user_organization_link uol ON o.id = uol.org_id " \
                    "INNER JOIN total_karma tk ON uol.user_id = tk.user_id GROUP BY o.title; "
            conn = engine.connect()
            # result = conn.execute(s).fetchall()
            rows = conn.execute(dba.text(query)).fetchall()
            conn.close()
            engine.dispose()
            # return result
            return rows

        except Exception as e:
            logger.exception(e)
            return e