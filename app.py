import streamlit as st
import pandas as pd
import mysql.connector

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="TMDB Movie Analytics",
    page_icon="🎬",
    layout="wide"
)

# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_connection():

    connection = mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        ssl_ca=st.secrets["mysql"]["ssl_ca"],
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )

    return connection
# 2. READ SQL RESULTS INTO PANDAS

def read_query(connection, sql_query):
    cursor = connection.cursor()

    try:
        cursor.execute(sql_query)

        rows = cursor.fetchall()

        columns = [column[0] for column in cursor.description]

        df = pd.DataFrame(rows, columns=columns)

        return df

    finally:
        cursor.close()

# ==========================================
# 3. LOAD DATABASE TABLES
# ==========================================

@st.cache_data(ttl=300)
def load_data():

    connection = get_connection()

    try:

        movies = read_query(
            connection,
            "SELECT * FROM movies"
        )

        genres = read_query(
            connection,
            "SELECT * FROM genres"
        )

        movie_genres = read_query(
            connection,
            "SELECT * FROM movie_genres"
        )

        cast_df = read_query(
            connection,
            "SELECT movie_id, person_id, actor_name FROM `cast`"
        )

        crew = read_query(
            connection,
            "SELECT movie_id, person_id, person_name, job, department FROM crew"
        )

        movie_keywords = read_query(
            connection,
            "SELECT movie_id, keyword_id, keyword_name FROM movie_keywords"
        )

    finally:
        connection.close()

    return (
        movies,
        genres,
        movie_genres,
        cast_df,
        crew,
        movie_keywords
    )


# ==========================================
# 4. LOAD DATA INTO PYTHON
# ==========================================

try:

    movies, genres, movie_genres, cast_df, crew, movie_keywords = load_data()

except Exception as e:

    st.error("Database loading failed.")

    st.exception(e)

    st.stop()


# ==========================================
# 5. DATA CLEANING FOR FILTERING
# ==========================================

movies["release_date"] = pd.to_datetime(
    movies["release_date"],
    errors="coerce"
)

movies["vote_average"] = pd.to_numeric(
    movies["vote_average"],
    errors="coerce"
)

movies["budget"] = pd.to_numeric(
    movies["budget"],
    errors="coerce"
)

movies["revenue"] = pd.to_numeric(
    movies["revenue"],
    errors="coerce"
)

movies["release_year"] = movies["release_date"].dt.year


# ==========================================
# 6. APPLICATION TITLE
# ==========================================

st.title("🎬 TMDB Movie Analytics Dashboard")

st.write(
    "Explore movie information, ratings, genres and revenue."
)

st.divider()


# ==========================================
# 7. PAGE NAVIGATION
# ==========================================

st.sidebar.title("🎬 TMDB Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "Filters",
        "Dashboard",
        "Query Explorer"
    ]
)


# ==========================================
# 8. SHARED FILTERS
# ==========================================

st.sidebar.header("Movie Filters")

# Genre options
genre_options = sorted(
    genres["genre_name"].dropna().unique().tolist()
)

selected_genres = st.sidebar.multiselect(
    "Select Genre",
    options=genre_options,
    default=[],
    key="selected_genres"
)

# Release year options
valid_years = movies["release_year"].dropna()

if len(valid_years) > 0:

    min_year = int(valid_years.min())
    max_year = int(valid_years.max())

    if min_year == max_year:
        year_range = (min_year, max_year)
    else:
        year_range = st.sidebar.slider(
            "Release Year Range",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            key="year_range"
        )

else:

    year_range = (1900, 2100)

# Minimum rating
min_rating = st.sidebar.slider(
    "Minimum Rating",
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.5,
    key="min_rating"
)

# Language options
language_options = sorted(
    movies["original_language"]
    .dropna()
    .unique()
    .tolist()
)

selected_language = st.sidebar.selectbox(
    "Select Language",
    options=["All"] + language_options,
    key="selected_language"
)


# ==========================================
# 9. APPLY FILTERS TO MOVIES
# ==========================================

filtered_movies = movies.copy()

# Filter by genre
if selected_genres:

    selected_genre_ids = genres.loc[
        genres["genre_name"].isin(selected_genres),
        "genre_id"
    ]

    selected_movie_ids = movie_genres.loc[
        movie_genres["genre_id"].isin(selected_genre_ids),
        "movie_id"
    ].unique()

    filtered_movies = filtered_movies[
        filtered_movies["movie_id"].isin(selected_movie_ids)
    ]

# Filter by release year
filtered_movies = filtered_movies[
    filtered_movies["release_year"].between(
        year_range[0],
        year_range[1]
    )
]

# Filter by minimum rating
filtered_movies = filtered_movies[
    filtered_movies["vote_average"].fillna(0) >= min_rating
]

# Filter by language
if selected_language != "All":

    filtered_movies = filtered_movies[
        filtered_movies["original_language"] == selected_language
    ]


# ==========================================
# 10. LIVE FILTER COUNT
# ==========================================

st.sidebar.divider()

st.sidebar.metric(
    "Matching Movies",
    f"{len(filtered_movies):,}"
)


# ==========================================
# 11. PAGE 1 - FILTERS
# ==========================================

if page == "Filters":

    st.header("🔍 Movie Filters")

    st.write(
        "Choose your preferred filters from the left sidebar."
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Matching Movies",
        f"{len(filtered_movies):,}"
    )

    col2.metric(
        "Selected Genres",
        len(selected_genres)
    )

    col3.metric(
        "Minimum Rating",
        min_rating
    )

    col4.metric(
        "Selected Language",
        selected_language
    )

    st.divider()

    st.subheader("Filtered Movie Results")

    st.dataframe(
        filtered_movies[
            [
                "movie_id",
                "title",
                "original_language",
                "release_date",
                "vote_average",
                "budget",
                "revenue"
            ]
        ].head(20),
        width="stretch"
    )

    st.success(
        f"Successfully found {len(filtered_movies):,} matching movies!"
    )


# =========================================================
# 12. PAGE 2 - DASHBOARD
# =========================================================

elif page == "Dashboard":

    st.header("📊 Movie Analytics Dashboard")

    dashboard_movies = filtered_movies.copy()

    # KPI calculations
    total_movies = len(dashboard_movies)

    filtered_genre_data = movie_genres.merge(
        dashboard_movies[["movie_id"]],
        on="movie_id",
        how="inner"
    )

    total_genres = filtered_genre_data["genre_id"].nunique()

    filtered_actor_data = cast_df.merge(
        dashboard_movies[["movie_id"]],
        on="movie_id",
        how="inner"
    )

    total_actors = filtered_actor_data["actor_name"].nunique()

    average_rating = dashboard_movies["vote_average"].mean()

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Movies", f"{total_movies:,}")
    col2.metric("Total Genres", f"{total_genres:,}")
    col3.metric("Total Actors", f"{total_actors:,}")

    col4.metric(
        "Average Rating",
        f"{average_rating:.2f}" if pd.notna(average_rating) else "N/A"
    )

    st.divider()

    # -----------------------------------------
    # 2. TOP 10 MOVIES BY REVENUE
    # -----------------------------------------

    st.subheader("🏆 Top 10 Movies by Revenue")

    revenue_data = dashboard_movies.copy()

    revenue_data["revenue"] = pd.to_numeric(
        revenue_data["revenue"], errors="coerce"
    )

    top_movies = (
        revenue_data[revenue_data["revenue"] > 0]
        .sort_values("revenue", ascending=False)
        .head(10)
    )

    if not top_movies.empty:

        chart_data = top_movies.set_index("title")[["revenue"]]

        st.bar_chart(chart_data)

        st.write(
            "Insight: These are the ten highest-revenue movies "
            "within the selected filters."
        )

    else:
        st.info("No revenue data available for the selected filters.")

    st.divider()

    # -----------------------------------------
    # 3. MOVIE DISTRIBUTION BY GENRE
    # -----------------------------------------

    st.subheader("🎭 Movie Distribution by Genre")

    genre_movies = movie_genres.merge(
        dashboard_movies[["movie_id"]],
        on="movie_id",
        how="inner"
    )

    genre_data = genre_movies.merge(
        genres[["genre_id", "genre_name"]],
        on="genre_id",
        how="left"
    )

    genre_counts = (
        genre_data.groupby("genre_name")["movie_id"]
        .nunique()
        .sort_values(ascending=False)
    )

    if not genre_counts.empty:

        st.bar_chart(genre_counts)

        st.write(
            f"Insight: {genre_counts.index[0]} "
            f"has the highest number of movies in the selected data."
        )

    else:
        st.info("No genre information available.")

    st.divider()

    # -----------------------------------------
    # 4. BUDGET VS REVENUE
    # -----------------------------------------

    st.subheader("💰 Budget vs Revenue Analysis")

    scatter_data = dashboard_movies[
        ["title", "budget", "revenue"]
    ].copy()

    scatter_data["budget"] = pd.to_numeric(
        scatter_data["budget"], errors="coerce"
    )

    scatter_data["revenue"] = pd.to_numeric(
        scatter_data["revenue"], errors="coerce"
    )

    scatter_data = scatter_data.dropna(
        subset=["budget", "revenue"]
    )

    scatter_data = scatter_data[
        (scatter_data["budget"] > 0) &
        (scatter_data["revenue"] > 0)
    ]

    if not scatter_data.empty:

        st.scatter_chart(
            scatter_data,
            x="budget",
            y="revenue",
            x_label="Budget",
            y_label="Revenue"
        )

        st.write(
            "Insight: The scatter plot helps examine the relationship "
            "between movie budgets and revenue."
        )

    else:
        st.info("No valid budget and revenue data available.")

    st.divider()

    # -----------------------------------------
    # 5. HIGHEST-GROSSING GENRE
    # -----------------------------------------

    st.subheader("⭐ Highest-Grossing Genre")

    revenue_genres = dashboard_movies[
        ["movie_id", "revenue"]
    ].merge(
        movie_genres,
        on="movie_id",
        how="inner"
    ).merge(
        genres[["genre_id", "genre_name"]],
        on="genre_id",
        how="left"
    )

    revenue_genres["revenue"] = pd.to_numeric(
        revenue_genres["revenue"], errors="coerce"
    )

    revenue_genres = revenue_genres.dropna(
        subset=["genre_name", "revenue"]
    )

    highest_genre = (
        revenue_genres.groupby("genre_name")["revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    if not highest_genre.empty:

        st.success(
            f"Highest-grossing genre: {highest_genre.index[0]}"
        )

        st.write(
            f"Total attributed revenue: "
            f"{highest_genre.iloc[0]:,.0f}"
        )

    else:
        st.info("No genre revenue information available.")


# =========================================================
# 13. PAGE 3 - QUERY EXPLORER (10 SQL QUERIES)
# =========================================================

elif page == "Query Explorer":

    st.header("🔎 TMDB SQL Query Explorer")

    st.write(
        "Explore 10 SQL analysis questions using your "
        "TMDB database."
    )

    st.info(
        "Select a SQL query to view its results, "
        "visualization and business insight."
    )

    st.divider()

    # -----------------------------------------------------
    # 1. SAVED QUERY DROPDOWN
    # -----------------------------------------------------

    query_options = [
        "Q1 - Action Movies Released After 2015",
        "Q2 - Top 10 Highest-Grossing Movies",
        "Q3 - Average Budget and Revenue by Genre",
        "Q4 - Top 10 Actors by Movie Count",
        "Q5 - Directors with More Than 3 Movies",
        "Q6 - Top 10 Most Used Keywords",
        "Q7 - Above Average Budget and Below Average Revenue",
        "Q8 - Actors in Christopher Nolan Movies",
        "Q9 - Highest Average Rating by Genre",
        "Q10 - Top 10 Movies by Number of Keywords"
    ]

    selected_query = st.selectbox(
        "📌 Select SQL Analysis Query",
        query_options
    )

    st.divider()

    # -----------------------------------------------------
    # 2. SQL QUERY DEFINITIONS
    # -----------------------------------------------------

    sql_queries = {

        # Q1
        query_options[0]: """
            SELECT
                m.title,
                m.release_date
            FROM movies m
            JOIN movie_genres mg
                ON m.movie_id = mg.movie_id
            JOIN genres g
                ON mg.genre_id = g.genre_id
            WHERE g.genre_name = 'Action'
                AND m.release_date >= '2016-01-01'
            ORDER BY m.release_date DESC
        """,

        # Q2
        query_options[1]: """
            SELECT
                tm.movie_id,
                tm.title,
                tm.revenue,
                GROUP_CONCAT(
                    g.genre_name
                    ORDER BY g.genre_name
                    SEPARATOR ', '
                ) AS genres
            FROM (
                SELECT
                    movie_id,
                    title,
                    revenue
                FROM movies
                WHERE revenue > 0
                ORDER BY revenue DESC
                LIMIT 10
            ) tm
            LEFT JOIN movie_genres mg
                ON tm.movie_id = mg.movie_id
            LEFT JOIN genres g
                ON mg.genre_id = g.genre_id
            GROUP BY
                tm.movie_id,
                tm.title,
                tm.revenue
            ORDER BY tm.revenue DESC
        """,

        # Q3
        query_options[2]: """
            SELECT
                g.genre_name,
                ROUND(AVG(m.budget), 2) AS average_budget,
                ROUND(AVG(m.revenue), 2) AS average_revenue
            FROM movies m
            JOIN movie_genres mg
                ON m.movie_id = mg.movie_id
            JOIN genres g
                ON mg.genre_id = g.genre_id
            GROUP BY g.genre_name
            ORDER BY average_revenue DESC
        """,

        # Q4
        query_options[3]: """
            SELECT
                c.person_id,
                c.actor_name,
                COUNT(DISTINCT c.movie_id) AS total_movies
            FROM `cast` c
            GROUP BY
                c.person_id,
                c.actor_name
            ORDER BY total_movies DESC
            LIMIT 10
        """,

        # Q5
        query_options[4]: """
            SELECT
                cw.person_id,
                cw.person_name,
                COUNT(DISTINCT cw.movie_id) AS total_movies
            FROM crew cw
            WHERE cw.job = 'Director'
            GROUP BY
                cw.person_id,
                cw.person_name
            HAVING COUNT(DISTINCT cw.movie_id) > 3
            ORDER BY total_movies DESC
        """,

        # Q6
        query_options[5]: """
            SELECT
                mk.keyword_id,
                mk.keyword_name,
                COUNT(DISTINCT mk.movie_id) AS total_movies
            FROM movie_keywords mk
            GROUP BY
                mk.keyword_id,
                mk.keyword_name
            ORDER BY total_movies DESC
            LIMIT 10
        """,

        # Q7
        query_options[6]: """
            SELECT
                m.movie_id,
                m.title,
                m.budget,
                m.revenue
            FROM movies m
            WHERE m.budget > (
                SELECT AVG(budget)
                FROM movies
            )
            AND m.revenue < (
                SELECT AVG(revenue)
                FROM movies
            )
            ORDER BY m.budget DESC
        """,

        # Q8
        query_options[7]: """
            SELECT DISTINCT
                c.actor_name,
                m.movie_id,
                m.title,
                cr.job,
                cr.person_name,
                cr.department
            FROM `cast` c
            JOIN movies m
                ON c.movie_id = m.movie_id
            JOIN crew cr
                ON m.movie_id = cr.movie_id
            WHERE cr.person_name = 'Christopher Nolan'
                AND cr.job = 'Director'
            ORDER BY m.title
        """,

        # Q9
        query_options[8]: """
            SELECT
                g.genre_name,
                ROUND(AVG(m.vote_average), 2) AS average_rating,
                COUNT(DISTINCT m.movie_id) AS total_movies
            FROM movies m
            JOIN movie_genres mg
                ON m.movie_id = mg.movie_id
            JOIN genres g
                ON mg.genre_id = g.genre_id
            GROUP BY g.genre_name
            HAVING COUNT(DISTINCT m.movie_id) >= 20
            ORDER BY average_rating DESC
        """,

        # Q10
        query_options[9]: """
            SELECT
                m.movie_id,
                m.title,
                COUNT(DISTINCT mk.keyword_id) AS total_keywords
            FROM movies m
            JOIN movie_keywords mk
                ON m.movie_id = mk.movie_id
            GROUP BY
                m.movie_id,
                m.title
            ORDER BY total_keywords DESC
            LIMIT 10
        """
    }

    # -----------------------------------------------------
    # 3. EXECUTE SELECTED SQL QUERY
    # -----------------------------------------------------

    st.subheader("💻 Selected SQL Query")

    st.code(
        sql_queries[selected_query],
        language="sql"
    )

    try:

        connection = get_connection()

        try:

            result = read_query(
                connection,
                sql_queries[selected_query]
            )

        finally:

            connection.close()

    except Exception as e:

        st.error("SQL query execution failed.")

        st.exception(e)

        st.stop()

    # -----------------------------------------------------
    # 4. DISPLAY DATAFRAME
    # -----------------------------------------------------

    st.divider()

    st.subheader("📋 Query Results")

    st.metric(
        "Total Records Found",
        f"{len(result):,}"
    )

    st.dataframe(
        result,
        width="stretch",
        hide_index=True
    )

    # -----------------------------------------------------
    # 5. DISPLAY CHART
    # -----------------------------------------------------

    st.divider()

    st.subheader("📊 Query Visualization")

    if result.empty:

        st.warning("No records found for this query.")

    else:

        # Q1 - Action Movies by Release Year

        if selected_query == query_options[0]:

            chart_data = result.copy()

            chart_data["release_date"] = pd.to_datetime(
                chart_data["release_date"],
                errors="coerce"
            )

            chart_data["release_year"] = (
                chart_data["release_date"].dt.year
            )

            chart_data = (
                chart_data.dropna(subset=["release_year"])
                .groupby("release_year")["title"]
                .count()
                .reset_index(name="total_movies")
                .set_index("release_year")
            )

            st.bar_chart(chart_data)

        # Q2 - Top 10 Movies by Revenue

        elif selected_query == query_options[1]:

            chart_data = result.set_index("title")[["revenue"]]

            st.bar_chart(chart_data)

        # Q3 - Average Budget and Revenue by Genre

        elif selected_query == query_options[2]:

            chart_data = result.set_index("genre_name")[
                ["average_budget", "average_revenue"]
            ]

            st.bar_chart(chart_data)

        # Q4 - Top 10 Actors

        elif selected_query == query_options[3]:

            chart_data = result.set_index("actor_name")[
                ["total_movies"]
            ]

            st.bar_chart(chart_data)

        # Q5 - Directors

        elif selected_query == query_options[4]:

            chart_data = result.set_index("person_name")[
                ["total_movies"]
            ]

            st.bar_chart(chart_data)

        # Q6 - Most Used Keywords

        elif selected_query == query_options[5]:

            chart_data = result.set_index("keyword_name")[
                ["total_movies"]
            ]

            st.bar_chart(chart_data)

        # Q7 - Budget vs Revenue

        elif selected_query == query_options[6]:

            chart_data = result[
                ["budget", "revenue"]
            ].apply(
                pd.to_numeric,
                errors="coerce"
            ).dropna()

            chart_data = chart_data[
                (chart_data["budget"] > 0) &
                (chart_data["revenue"] > 0)
            ]

            if not chart_data.empty:

                st.scatter_chart(
                    chart_data,
                    x="budget",
                    y="revenue",
                    x_label="Movie Budget",
                    y_label="Movie Revenue"
                )

            else:

                st.info("No valid budget and revenue values for chart.")

        # Q8 - Christopher Nolan Movies

        elif selected_query == query_options[7]:

            chart_data = (
                result.groupby("title")["actor_name"]
                .nunique()
                .reset_index(name="total_actors")
                .sort_values("total_actors", ascending=False)
                .set_index("title")
            )

            st.bar_chart(chart_data)

        # Q9 - Highest Average Rating by Genre

        elif selected_query == query_options[8]:

            chart_data = result.set_index("genre_name")[
                ["average_rating"]
            ]

            st.bar_chart(chart_data)

        # Q10 - Movies with Most Keywords

        elif selected_query == query_options[9]:

            chart_data = result.set_index("title")[
                ["total_keywords"]
            ]

            st.bar_chart(chart_data)

    # -----------------------------------------------------
    # 6. BUSINESS INSIGHT
    # -----------------------------------------------------

    st.divider()

    st.subheader("💡 Insight")

    insight = ""

    if result.empty:

        insight = "No data is available for this SQL analysis."

    else:

        # Q1
        if selected_query == query_options[0]:

            insight = (
                f"Found {len(result)} Action movies released "
                "from 2016 onwards. "
                "This analysis helps understand recent "
                "Action movie production."
            )

        # Q2
        elif selected_query == query_options[1]:

            insight = (
                f"{result.iloc[0]['title']} is the highest "
                f"revenue-generating movie in this result, "
                f"with revenue of "
                f"{result.iloc[0]['revenue']:,.0f}. "
                f"Its genres are {result.iloc[0]['genres']}."
            )

        # Q3
        elif selected_query == query_options[2]:

            insight = (
                f"{result.iloc[0]['genre_name']} has the "
                f"highest average revenue among the genres. "
                f"Average revenue: "
                f"{result.iloc[0]['average_revenue']:,.2f}."
            )

        # Q4
        elif selected_query == query_options[3]:

            insight = (
                f"{result.iloc[0]['actor_name']} appears in "
                f"{result.iloc[0]['total_movies']} movies "
                "and ranks first among the top 10 actors."
            )

        # Q5
        elif selected_query == query_options[4]:

            insight = (
                f"{result.iloc[0]['person_name']} has directed "
                f"{result.iloc[0]['total_movies']} movies. "
                "The results include directors who have "
                "directed more than 3 movies."
            )

        # Q6
        elif selected_query == query_options[5]:

            insight = (
                f"The most frequently used keyword is "
                f"{result.iloc[0]['keyword_name']}, "
                f"appearing in "
                f"{result.iloc[0]['total_movies']} movies."
            )

        # Q7
        elif selected_query == query_options[6]:

            insight = (
                f"Found {len(result)} movies with a budget "
                "above the overall average budget and "
                "revenue below the overall average revenue. "
                "These movies may indicate higher investment "
                "with relatively weaker revenue performance."
            )

        # Q8
        elif selected_query == query_options[7]:

            total_actors = result["actor_name"].nunique()

            total_movies = result["movie_id"].nunique()

            insight = (
                f"Found {total_actors} distinct actors across "
                f"{total_movies} movies directed by "
                "Christopher Nolan."
            )

        # Q9
        elif selected_query == query_options[8]:

            insight = (
                f"{result.iloc[0]['genre_name']} has the "
                f"highest average rating of "
                f"{result.iloc[0]['average_rating']:.2f}, "
                f"based on {result.iloc[0]['total_movies']} "
                "movies. Only genres with at least 20 movies "
                "are included."
            )

        # Q10
        elif selected_query == query_options[9]:

            insight = (
                f"{result.iloc[0]['title']} has the highest "
                f"number of keywords, with "
                f"{result.iloc[0]['total_keywords']} keywords."
            )

    st.text_area(
        "Analysis and Interpretation",
        value=insight,
        height=120,
        disabled=True
    )

    st.success(
        f"SQL Analysis Completed: {selected_query}"
    )

#python -m streamlit run app.py --server.port 8504