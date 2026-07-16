import os
from urllib.parse import urlparse
from tornado.httpserver import HTTPServer
from tornado.httpclient import AsyncHTTPClient
from tornado.web import Application, HTTPError, RequestHandler, authenticated
from tornado.ioloop import IOLoop
from jupyterhub.services.auth import HubOAuthenticated, HubOAuthCallbackHandler
import requests
import json


def event_stream(session, url):
    """Generator yielding events from a JSON event stream

    For use with the server progress API
    """
    r = session.get(url, stream=True)
    r.raise_for_status()
    for line in r.iter_lines():
        line = line.decode('utf8', 'replace')
        # event lines all start with `data:`
        # all other lines should be ignored (they will be empty)
        if line.startswith('data:'):
            yield json.loads(line.split(':', 1)[1])
def start_server(session, hub_url, user, server_name=""):
    """Start a server for a jupyterhub user

    Returns the full URL for accessing the server
    """
    user_url = f"{hub_url}/jupyter/hub/api/users/{user}"
    log_name = f"{user}/{server_name}".rstrip("/")

    # step 1: get user status
    r = session.get(user_url)
    r.raise_for_status()
    user_model = r.json()

    # if server is not 'active', request launch
    if server_name not in user_model.get('servers', {}):
        # log.info(f"Starting server {log_name}")
        r = session.post(f"{user_url}/servers/{server_name}")
        r.raise_for_status()
        r = session.get(user_url)
        r.raise_for_status()
        user_model = r.json()

    # report server status
    server = user_model['servers'][server_name]
    if server['pending']:
        status = f"pending {server['pending']}"
    elif server['ready']:
        status = "ready"
    else:
        # shouldn't be possible!
        raise ValueError(f"Unexpected server state: {server}")

    # wait for server to be ready using progress API
    progress_url = user_model['servers'][server_name]['progress_url']
    for event in event_stream(session, f"{hub_url}{progress_url}"):
        if event.get("ready"):
            server_url = event['url']
            break
    else:
        # server never ready
        raise ValueError(f"{log_name} never started!")

    # at this point, we know the server is ready and waiting to receive requests
    # return the full URL where the server can be accessed
    return server_url


class ChartServiceHandler(HubOAuthenticated, RequestHandler):
    def initialize(self):
        self.hub_auth.hub_prefix = '/jupyter'
        self.hub_auth.oauth_client_id = 'service-chart-service'
        self.hub_auth.oauth_redirect_uri = '/jupyter/services/chart-service/oauth_callback/'
        self.hub_auth.api_url = 'http://jupyterhub:8000/jupyter/hub/api/'
        self.hub_host = 'http://jupyterhub:8000'
    @authenticated
    def get(self):
        token = self.hub_auth.get_token(self)
        user =  self.get_current_user()
        session = requests.Session()
        session.headers = {"Authorization": f"token {token}"}
        config = json.loads(self.get_argument('config'))
        title = config['title']
        notebook = notebook_generation(config)
        server_url = start_server(session, self.hub_host,user.get('name'))  
        response = session.put(f'{self.hub_host}{server_url}api/contents/{title}.ipynb',headers={'Content-Type': 'application/json'}, json={
            'content': notebook,
            'type': 'notebook',
        })
        print(response, flush=True)
        self.redirect(server_url)
    def post(self):
        data = json.loads(self.request.body)
        self.config = data
        print(self.config, flush=True)      
        self.write('Data Received')
        
 #'/rest/auth/jwt-redirect'    
        
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')    
    def options(self, *args):
        # no body
        # `*args` is for route with `path arguments` supports
        self.set_status(204)
        self.finish()        

#   metrics needed=
#   timeframe_label, start_date, end_date, aggregation_unit,
#   timeseries, swap_xy, global_filters.total, global_filters.data
#   data_series.total, data_series.data, title

def notebook_generation(config):
    ret_json = {
                'metadata': {
                    'kernel_info': {
                        'name': 'Python 3'
                    },
                    'language_info': {
                        'name': 'Python',
                        'version': 'the version of the language',
                        'codemirror_mode': 'The name of the codemirror mode to use [optional]',
                    },
                },
                'nbformat': 4,
                'nbformat_minor': 0,
                'cells': [
                    create_cell('markdown', 'The following cell includes all the necessary imports.  Currently, must run XDMOD-Data-First-Example at least once in order for any generated code to work.'),
                    create_cell('code', 'import plotly.express as px\nimport plotly.io as pio\nimport pandas as pd\nimport plotly.graph_objects as go\nimport xdmod_data.themes\npio.templates.default = "timeseries"'),
                    create_cell('code', 'import os\nos.environ["JUPYTERHUB_API_TOKEN"] = "placeholder"'),
                    create_cell('code', 'from xdmod_data.warehouse import DataWarehouse\ndw = DataWarehouse()')
                ]
            }
    timeframe_label = config.get("timeframe_label")
    start_date = config.get("start_date")
    end_date = config.get("end_date")

    if timeframe_label == "User Defined" and start_date and end_date:
        duration = f"{start_date}' , '{end_date}"
    elif timeframe_label:
        duration = timeframe_label
    else:
        duration = "Previous Month"

    # ---- x axis label formatting -----------------------------------------
    # get the distance from start and end date and determine how to display x values
    duration_dist = int(end_date[:4]) - int(start_date[:4])
    aggregation_unit_raw = config.get("aggregation_unit")

    if duration_dist < 1 or aggregation_unit_raw == "Day":
        x_value_labels = ""
    elif duration_dist < 10 or aggregation_unit_raw == "Month":
        x_value_labels = "xaxis_tickformat = '%b %Y'"
    elif duration_dist >= 10 or aggregation_unit_raw == "Quarter":
        x_value_labels = "xaxis_tickformat = 'Q%q %Y'"
    elif aggregation_unit_raw == "Year":
        x_value_labels = "xaxis_tickformat = '%Y'"
    else:
        x_value_labels = ""

    data_type = "timeseries" if config.get("timeseries") else "aggregate"
    aggregation_unit = aggregation_unit_raw or "Auto"
    swap_xy = config.get("swap_xy")

    # ---- filters ----------------------------------------------------------
    filters = ""
    filter_dict = {}
    sub_title = ""

    global_filters = config.get("global_filters", {"total": 0, "data": []})
    for i in range(global_filters.get("total")):
        entry = global_filters["data"][i]
        dim_id = entry["dimension_id"]
        value = entry["value_name"]
        filter_dict.setdefault(dim_id, []).append(value)

    for dim_id, values in filter_dict.items():
        joined = "', '".join(values)
        filters += f"\n\t\t'{dim_id}': ('{joined}'),"
        sub_title += f"{dim_id}: {joined.replace("'", '')}"

    # ---- setup for the data-fetch / plot-building loop --------------------
    data_calls = "# Call to Data Analytics Framework requesting data \nwith dw:"

    data_series = config["data_series"]
    plot_chart = "" if data_series["total"] == 1 else "plot = go.Figure()\n"

    # code appended at the end of the last cell (updates layout of created charts)
    update_layout = "\n\n# Format and label the axes\nplot.update_layout("

    is_spline = False

    # check if multiple realms / metrics
    multiple_realms = False
    multiple_metrics = False
    comp_realm = data_series["data"][0]["realm"]
    comp_metric = config['data_series']['data'][0]['metric_text']

    for i in range(data_series["total"]):
        entry = data_series["data"][i]
        if entry["realm"] != comp_realm:
            multiple_realms = True
        if entry["metric_text"] != comp_metric:
            multiple_metrics = True

    def rename_cols_code(i: int, realm: str, dimension: str) -> str:
        """code for renaming columns if multiple metrics or realms"""
        realm_label = "Resource Specifications" if realm == "ResourceSpecifications" else realm
        dept_expr = "'ACCESS'" if dimension == "none" else "col"

        if multiple_metrics and multiple_realms:
            return (
                f"\n# Rename column names to specify Realm and/or Metric\n"
                f"newColNames = {{}}\n"
                f"for col in data_{i}.columns :\n"
                f"    newColNames[col] = '{realm_label}: ' + {dept_expr} + ' [' + label_{i} + ']'\n"
                f"data_{i} = data_{i}.rename(columns=newColNames)"
            )
        elif multiple_metrics:
            return (
                f"\n# Rename column names to specify Realm and/or Metric\n"
                f"newColNames = {{}} \n"
                f"for col in data_{i}.columns :\n"
                f"    newColNames[col] = {dept_expr} + ' [' + label_{i} + ']'\n"
                f"data_{i} = data_{i}.rename(columns=newColNames)"
            )
        elif multiple_realms:
            return (
                f"\n# Rename column names to specify Realm and/or Metric\n"
                f"newColNames = {{}}\n"
                f"for col in data_{i}.columns :\n"
                f"    newColNames[col] = '{realm_label}: ' + {dept_expr}\n"
                f"data_{i} = data_{i}.rename(columns=newColNames)"
            )
        return ""

    # side of y label switches after each axes plotted
    curr_side = "left"
    # tracks which metrics are used so repeated metrics get merged into the
    # dataset previously fetched for that same metric
    metrics_list = {}

    # ---- main loop over data series ---------------------------------------
    for i in range(data_series["total"]):
        entry = data_series["data"][i]
        if entry.get("enabled") is False:  # disable toggle check
            continue

        realm = entry.get("realm", "Jobs")
        metric = entry.get("metric", "CPU Hours: Total")
        dimension = entry.get("group_by", "none")
        log_scale = entry.get("log_scale")
        display_type = entry.get("display_type")

        graph_type = display_type or "line"
        line_shape = ""

        if graph_type == "column":
            graph_type = "bar"
            line_shape = "barmode='group',"
        elif graph_type == "spline":
            is_spline = True
            graph_type = "line"
            line_shape = "\nline_shape='spline',"
        elif graph_type == "line" and data_type == "aggregate" and dimension == "none":
            graph_type = "scatter"
        elif graph_type == "areaspline":
            is_spline = True
            graph_type = "area"
            line_shape = "\nline_shape='spline',"

        # Checks if metric used in a previous dataset; if not, add for future reference
        metric_text = entry['metric_text']
        if metric_text in metrics_list:
            # metric used in a previous data series: merge with it and move on
            data_calls += f"""
\n# Fetch data {i}
    data_{i} = dw.get_data(
    duration=('{duration}'),
    realm='{realm}',
    metric='{metric}',
    dimension='{dimension}',
    filters={{{filters}}},
    dataset_type='{data_type}',
    aggregation_unit='{aggregation_unit}',
)
    \n# Set data {i}'s metric label
    label_{i} = dw.describe_metrics('{realm}').loc['{metric}', 'label']
    {rename_cols_code(i, realm, dimension)}
    \n# Merge data {i} into data {metrics_list[metric_text]} since they share the same metric
    data_{metrics_list[metric_text]} = (data_{metrics_list[metric_text]}.merge(data_{i}, on='Time', how='outer', sort=True))"""
            continue
        else:
            metrics_list[metric_text] = i

        # if metric never used, fetch and plot normally
        if swap_xy and graph_type != "pie":
            axis = f"\ty= data_{i}.columns[0],\n\tx= data_{i}.columns[1:],"
        else:
            axis = f'labels={{"value": label_{i}}},'

        if data_type == "aggregate":
            if graph_type == "pie":
                graph = f"""
if(data_{i}.size > 10):
    others_sum=data_{i}[~data_{i}.isin(top_ten)].sum()
    data_{i} = top_ten.combine_first(pd.Series({{'Other ' + str(data_{i}.size - 10): others_sum}}))\n"""
            else:
                graph = f"\ndata_{i} = top_ten"
            data_view = f"""
\n# Process the data series, combine the lower values into a single Other category, and change to series to a dataframe
top_ten=data_{i}.nlargest(10)
{graph}
data_{i} = data_{i}.to_frame()
columns_list = data_{i}.columns.tolist()"""
        else:
            data_view = f"""
\n# Limit the number of data items/source to at most 10 and sort by descending
columns_list = data_{i}.columns.tolist()
if (len(columns_list) > 10):
    column_sums = data_{i}.sum()
    top_ten_columns = column_sums.nlargest(10).index.tolist()
    data_{i} = data_{i}[top_ten_columns]"""

        data_calls += f"""
    \n# Fetch data {i}
    data_{i} = dw.get_data(
        duration=('{duration}'),
        realm='{realm}',
        metric='{metric}',
        dimension='{dimension}',
        filters={{{filters}}},
        dataset_type='{data_type}',
        aggregation_unit='{aggregation_unit}',
    )
    \n# Set data {i}'s metric label
    label_{i} = dw.describe_metrics('{realm}').loc['{metric}', 'label']
    {rename_cols_code(i, realm, dimension)}"""

        plot_chart += f"""{data_view}
    {"data_0 = data_0.reset_index()" if (swap_xy and graph_type != "pie") else ""}"""

        if data_series["total"] == 1:
            log_axis = "x" if swap_xy else "y"
            title = config.get("title") or "Untitled Query"
            sub_title_html = f"<br><sup>{sub_title}</sup>," if sub_title else ""
            log_scale_code = f"log_{log_axis}=True," if log_scale else ""
            pie_args = "\nvalues= columns_list[0],\n names= data_0.index," if graph_type == "pie" else ""
            plot_chart += f"""
\n# Format and draw graph to the screen
plot = px.{graph_type}(
    data_0, {pie_args}
    {axis}
    title='{title}',{sub_title_html}{log_scale_code}{line_shape}
)\n"""
        else:
            bar_init = "i = 0" if (graph_type == "bar" and i == 0) else ""
            trace_type = "Bar" if graph_type == "bar" else "Scatter"
            fill_code = 'fill = "tozeroy",' if graph_type == "area" else ""
            spline_code = 'line_shape = "spline"' if is_spline else ""
            bar_offset = "offsetgroup = i" if graph_type == "bar" else ""
            bar_incr = "i += 1" if graph_type == "bar" else ""

            plot_chart += f"""
\\n# Add axis from dataset {i} to graph
{bar_init}
for col in data_{i}:
    plot.add_trace(
    go.{trace_type}(
        x=data_{i}.index,
        y=data_{i}[col].values,
        name = col,
        yaxis="y{i + 1}",
        {fill_code}
        {spline_code}
        {bar_offset}
    ))
    {bar_incr}"""
#may change axis_extra
            axis_extra = ""
            if i != 0:
                axis_extra = f"""
        anchor="free",
        overlaying="y",
        autoshift = True,
        side="{curr_side}\""""
            update_layout += f"""
    yaxis{i + 1}=dict(
        title=dict(
            text=label_{i},
        ),{axis_extra}
    ),"""

            # switch side
            curr_side = "left" if curr_side == "right" else "right"

    # when the axes are swapped, reverse the ordering of the y axis to match xdmod
    if swap_xy:
        update_layout += 'yaxis=dict(autorange="reversed")'

    update_layout += "\n)\n"
    plot_chart += (
        f"{update_layout}\n# Format legend and set index interval\n"
        f"plot.update_layout(legend_x=0, legend_y=-0.3, {x_value_labels})"
        f"{'\nplot.update_yaxes(showgrid=False)' if data_series['total'] > 1 else ''}"
        f"\n\nplot.show()"
    )

    ret_json["cells"].extend([
        create_cell(
            "markdown",
            "The following cell fetches all the necessary data from the data analytics framework",
        ),
        create_cell("code", data_calls),
        create_cell(
            "markdown",
            "The following cell uses the data fetched in the previous cell to plot the chart and display it",
        ),
        create_cell("code", plot_chart),
    ])
    return ret_json

def create_cell(type, source):
    cell = {
        'cell_type': type,
        'metadata': {},
        'source': source    
    }
    if (type == 'code'):
        cell['execution_count'] = 1
        cell['outputs'] = [{
            'output_type': 'stream',
            'name': 'stdout',
            'text': ''
        }]
    return cell
    

def main():
    application = Application([('/jupyter/services/chart-service', ChartServiceHandler), 
                               ('/jupyter/services/chart-service/oauth_callback/', HubOAuthCallbackHandler)],
                              cookie_secret=os.urandom(32), debug=True)
    http_server = HTTPServer(application)
    url = urlparse('http://0.0.0.0:2323')
    http_server.listen(url.port, url.hostname)
    IOLoop.current().start()
if __name__ == '__main__':
    main()
