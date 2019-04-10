$(document).ready(function () {
    var plot_div = $('#id_plot_session');
    // Set up a global variable for the names of the stats reported here
    // (in hopes of making it easier to keep line colors consistent
    var reportStats = [];
    fetch(plot_div.attr("data-url"))
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            // Plot data
            var parsedData = parseGameData(data);
            drawActionsTS(parsedData);
            drawDataTable(data['game_data']);
            // Make a vector for all of the stats, so that plot attributes can be
            // kept consistent - probably a better way to do this.
            d3.selectAll("tbody tr")
                .each(function (d) {
                    reportStats.push(d.key);
                });

        });

});


function parseGameData(data) {
    /**
     * Here we parse the json data received into the appropriate format for plotting.
     */
    var arr = [];
    for (var i = 0; i < data['game_data'].length; i++) {
        arr.push(
            {
                x: data['game_data'][i]['round'], //date
                y: data['game_data'][i].action //convert string to number
            });
    }
    return arr;
}

Array.prototype.move = function (from, to) {
  this.splice(to, 0, this.splice(from, 1)[0]);
};


function drawActionsTS(actions_ts) {
    var svgWidth = 600, svgHeight = 400;
    var margin = {top: 20, right: 20, bottom: 30, left: 50};
    var width = svgWidth - margin.left - margin.right;
    var height = svgHeight - margin.top - margin.bottom;
    var radius = 5;


    var svg = d3.select('#id_plot_session').append("svg")
        .attr("width", svgWidth)
        .attr("height", svgHeight)
        .attr("style", "border: 1px solid lightgray;");

    var g = svg.append("g")
        .attr("transform",
            "translate(" + margin.left + "," + margin.top + ")"
        );

    // add the tooltip area to the webpage
    var tooltip = d3.select("#id_plot_session").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);

    var x = d3.scaleLinear().rangeRound([0, width]);
    var y = d3.scaleLinear().rangeRound([height, 0]);

    x.domain(d3.extent(actions_ts, function (d) {
        return d.x
    }));
    y.domain(d3.extent(actions_ts, function (d) {
        return d.y
    }));

    g.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x))
        .select(".domain")
        .append("text")
        .text("rounds");


    g.append("g")
        .call(d3.axisLeft(y))
        .append("text")
        .attr("fill", "#000")
        .attr("transform", "rotate(-90)")
        .attr("class", "y axis")
        .attr("dy", "0.71em")
        .attr("text-anchor", "end")
        .text("Actions");

    //create svg element
    g.selectAll("circle")
        .data(actions_ts)
        .enter()
        .append("circle")
        .attr("cx", function (d) {
            return x(d.x);
        })
        .attr("cy", function (d) {
            return y(d.y);
        })
        .attr("r", radius)
        .attr("fill", "green")
        .on("mouseover", handleMouseOver)
        .on("mouseout", handleMouseOut);

    // Create Event Handlers for mouse
    function handleMouseOver(d) {  // Add interactivity
        tooltip.transition()
            .duration(200)
            .style("opacity", .9);
        tooltip.html("(" + d.x + ", " + d.y + ")")
            .style("left", (d3.event.pageX + 5) + "px")
            .style("top", (d3.event.pageY - 28) + "px");
    }

    function handleMouseOut(d, i) {
        tooltip.transition()
            .duration(500)
            .style("opacity", 0);
    }
}


/**
 * This function creates a table with features in a row and game rounds in the columns
 * @param data
 */
function drawDataTable(data) {
    var table = d3.select("#id_sess_data_table")
            .append("table")
            .attr("class", "table table-condensed table-striped"),
        thead = table.append("thead"),
        tbody = table.append("tbody");


    // Get every column value
    // var columns = Object.keys(data[0])
    // .filter(function (d) {
    //         return (d !== "time_round_ends" &&
    //             d !== "opponent_id" &&
    //             d !== "time_round_start" &&
    //             d !== "time_question_start" &&
    //             d !== "time_question_end"
    //         );
    //     });
    // columns.move(2, 0);
    var columns = ["id", "player_id", "group_id", "round", "action",
        "private_account", "public_account", "prediction_question", "time_elapsed",
        "time_question_elapsed", "session_id"];

    var header = thead.append("tr")
        .selectAll("th")
        .data(columns)
        .enter()
        .append("th")
        .text(function (d) {
            return d;
        })
        .on("click", function (d) {
            if (d === "player_id") {
                rows.sort(function (a, b) {
                    if (a[d] < b[d]) {
                        return -1;
                    }
                    if (a[d] > b[d]) {
                        return 1;
                    }
                    else {
                        return 0;
                    }
                });
            }
            else {
                rows.sort(function (a, b) {
                    return b[d] - a[d];
                })
            }
        });

    var rows = tbody.selectAll("tr")
        .data(data)
        .enter()
        .append("tr")
        .on("mouseover", function (d) {
            d3.select(this)
                .style("background-color", "orange");
        })
        .on("mouseout", function (d) {
            d3.select(this)
                .style("background-color", "transparent");
        });

    var cells = rows.selectAll("td")
        .data(function (row) {
            return columns.map(function (d, i) {
                return {i: d, value: row[d]};
            });
        })
        .enter()
        .append("td")
        .html(function (d) {
            return d.value;
        });

}
