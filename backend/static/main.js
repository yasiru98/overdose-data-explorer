
/* Variables */
let lowColor = '#f9f9f9'
let highColor = '#D33F49'
let ramp;
let minVal, maxVal;

// seriesByDate: "2015-01-31" -> { "Alabama": 715, "Alaska": 126, ... }
// one entry per rolling-12-month-ending period we got back from the API
let seriesByDate = new Map();
let dates = [];          // sorted list of period_end_date strings, drives the slider
let stateValues;         // the state->value map for whichever date is currently shown
let usStatesGeoJson;     // fetched once, reused for every redraw

var slide = document.getElementById('slide');
var sliderDiv = document.getElementById("sliderAmount");

/* UTILITY FUNCTIONS */

// turns "2015-01-31" into "January 2015" for display
function formatPeriodLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

function totalForDate(dateStr) {
  const values = Object.values(seriesByDate.get(dateStr));
  return values.reduce((sum, v) => sum + (v || 0), 0);
}

function updateSliderLabel(dateStr) {
  const total = Math.round(totalForDate(dateStr)).toLocaleString();
  sliderDiv.innerHTML = `<h1 class="text-xl-h1">${formatPeriodLabel(dateStr)}<br>${total} Deaths (12-mo ending)</h1>`;
}

function showDate(dateStr) {
  stateValues = seriesByDate.get(dateStr);
  updateSliderLabel(dateStr);
  d3.selectAll("svg > *").remove();
  createVisualization(usStatesGeoJson, stateValues);
}

slide.onchange = function () {
  showDate(dates[slide.value - 1]);
};

// Set tooltips
const tip = d3.tip()
  .attr('class', 'd3-tip')
  .offset([-10, 0])
  .html(d => {
    const value = stateValues[d.properties.name];
    const display = value == null ? 'Data not available' : value.toLocaleString();
    return `<strong>State: </strong><span class='details'>${d.properties.name}<br></span><strong>Deaths (12-mo ending): </strong><span class='details'>${display}</span>`;
  });

/* VISUALIZATION CODE */

const createVisualization = (dataset, stateValues) => {
  const w = 800, h = 600;

  const svg = d3.select("#choropleth")
    .attr('width', w)
    .attr('height', h);

  svg.call(tip);
  // 2. Define a map projection
	const projection = d3.geoAlbersUsa()
    .translate([w/2, h/2]);

  // 3. Define a path generator using the projection
  const path = d3.geoPath()
    .projection(projection);

  // shared between the main states and the Puerto Rico inset below, so both
  // look and behave the same instead of duplicating this logic twice
  const fillForFeature = d => {
    // some state/month combos have no value (CDC suppresses low-quality
    // data), fall back to a neutral gray instead of feeding null into the
    // color scale
    const value = stateValues[d.properties.name];
    return value == null ? '#cccccc' : ramp(value);
  };

  function handleMouseover(d) {
    tip.show(d);
    d3.select(this)
      .style('opacity', 1)
      .style('stroke-width', 3);
  }

  function handleMouseout(d) {
    tip.hide(d);
    d3.select(this)
      .style('opacity', 0.8)
      .style('stroke-width', 1);
  }

  // Puerto Rico is handled separately below (geoAlbersUsa can't place it),
  // so it's excluded here to avoid drawing an invisible duplicate path
  const statesOnly = dataset.features.filter(d => d.properties.name !== 'Puerto Rico');

  //Bind data and create one path per GeoJSON feature
  svg.selectAll("path.state")
      .data(statesOnly)
      .join('path')
      .attr("class", "state")
      .attr("d", path)
      .style("stroke", "#787878")
      .style("fill", fillForFeature)
      .on('mouseover', handleMouseover)
      .on('mouseout', handleMouseout);

  // geoAlbersUsa only knows how to place the continental US, Alaska, and
  // Hawaii (each is its own little inset projection under the hood) -
  // anything outside those three, like Puerto Rico, gets clipped to nothing
  // and silently fails to draw. so it gets its own small projection here,
  // fit into an empty patch of ocean southeast of Florida on the canvas -
  // same idea as how Alaska/Hawaii are already inset, just done by hand
  const prFeature = dataset.features.find(d => d.properties.name === 'Puerto Rico');
  if (prFeature) {
    const prProjection = d3.geoMercator()
      .fitExtent([[690, 480], [780, 560]], prFeature);
    const prPath = d3.geoPath().projection(prProjection);

    svg.append('path')
      .datum(prFeature)
      .attr('class', 'state')
      .attr('d', prPath)
      .style('stroke', '#787878')
      .style('fill', fillForFeature)
      .on('mouseover', handleMouseover)
      .on('mouseout', handleMouseout);
  }

      var key =  d3.select("#legend")
			.attr("width", 120)
			.attr("height", 700)
			.attr("class", "legend");

		var legend = key.append("defs")
			.append("svg:linearGradient")
			.attr("id", "gradient")
			.attr("x1", "100%")
			.attr("y1", "0%")
			.attr("x2", "100%")
			.attr("y2", "100%")
			.attr("spreadMethod", "pad");

		legend.append("stop")
			.attr("offset", "0%")
			.attr("stop-color", highColor)
			.attr("stop-opacity", 1);

		legend.append("stop")
			.attr("offset", "100%")
			.attr("stop-color", lowColor)
			.attr("stop-opacity", 1);

		key.append("rect")
			.attr("width", 100)
			.attr("height", h)
			.style("fill", "url(#gradient)")
			.attr("transform", "translate(-60,10)");

		let y = d3.scaleLinear()
			.range([h, 0])
			.domain([minVal, maxVal]);

		let yAxis = d3.axisRight(y);

		key.append("g")
			.attr("class", "y axis")
			.attr("transform", "translate(41,10)")
			.call(yAxis)
}

/* BOOTSTRAP: load everything once from our own backend, then wire up the slider */
function loadData(attempt = 1) {
  Promise.all([
    d3.json('/api/deaths'),
    d3.json('us-states.json')
  ]).then(([records, geojson]) => {
    usStatesGeoJson = geojson;

    records.forEach(r => {
      if (!seriesByDate.has(r.period_end_date)) {
        seriesByDate.set(r.period_end_date, {});
      }
      seriesByDate.get(r.period_end_date)[r.state_name] = r.data_value;
    });

    dates = Array.from(seriesByDate.keys()).sort();

    // fixed color scale domain across the WHOLE time range (not just whichever
    // month happens to be selected) so colors stay comparable as you scrub -
    // this is what was broken in the original version, where the ramp only
    // ever got built from 2014's numbers no matter what year you picked
    const allValues = records.map(r => r.data_value).filter(v => v != null);
    minVal = d3.min(allValues);
    maxVal = d3.max(allValues);
    ramp = d3.scaleLinear().domain([minVal, maxVal]).range([lowColor, highColor]);

    slide.min = 1;
    slide.max = dates.length;
    slide.step = 1;
    slide.value = dates.length;

    showDate(dates[dates.length - 1]); // start on the most recent month
  }).catch(err => {
    console.error('Failed to load data (attempt ' + attempt + '):', err);
    if (attempt < 3) {
      // the backend's database connection can occasionally be stale on the
      // first request after a period of inactivity (neon, our hosted
      // postgres, suspends when idle) and needs a moment to recover.
      // retry automatically instead of leaving the page stuck on "Loading..."
      // with no explanation and making the user refresh manually
      setTimeout(() => loadData(attempt + 1), 1500);
    } else {
      sliderDiv.innerHTML = '<h1 class="text-xl-h1">Something went wrong loading the data. Please refresh the page.</h1>';
    }
  });
}

loadData();
