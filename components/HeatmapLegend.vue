/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

Component to render a heatmap legend plot, based on heatmapData which must be supplied as input.
See 'secondaryData' key in demo_data.json for example data.

<template>
<div>
    <div id="heatmapLegendDiv">
        <p>Heatmap legend</p>
    </div>
</div>
</template>

<script>
import * as d3 from 'd3';
import {put_in_svg, rect, line, heatmap_legend_text, linear_gradient, text, text_centered, text_right_aligned} from "~/assets/svg_utils";

export default {
    props: ["heatmapData"],
    data: () => {
        return {
            show_isoform_heatmap: true,
            hide_isoform_heatmap_labels: false,
            logTransform: false
        };
    },

    methods: {
        buildHeatmapLegend() {
            // Clear the space of any content
            d3.select('#heatmapLegendDiv').selectAll('*').remove();

            if (!this.show_isoform_heatmap)
                return;

            let el = document.getElementById("heatmapDiv");
            if (!(el && this.heatmapData)) return;

            let data = JSON.parse(JSON.stringify(this.heatmapData.samples));
            data.splice(this.heatmapData.transcript_id_colnum, 1);

            for (let i = 0; i < data.length; ++i)
            {
                let sample = data[i].toLowerCase();
                if (sample === "gene_id")
                {
                    data.splice(i, 1);
                    break;
                }
            }

            let padding = 16;
            let boundary = el.getBoundingClientRect();
            let width = boundary.width - 2 * padding;

            let height = 0;
            let font_size = 16.0;
            let canvas_width = Math.ceil(width);
            let num_samples = data.length;
            let cell_width = canvas_width / num_samples;

            if (!this.hide_isoform_heatmap_labels)
            {
                d3.select("#heatmapLegendDiv").append("canvas").attr("id", "fontSizeCalcCanvas");
                let fontSizeCalcCanvas = document.getElementById("fontSizeCalcCanvas");
                let fontSizeCalcCanvas_ctx = fontSizeCalcCanvas.getContext("2d");

                fontSizeCalcCanvas_ctx.textBaseline = "bottom";
                while (font_size > 12.0)
                {
                    fontSizeCalcCanvas_ctx.font = `${font_size}px sans-serif`;
                    let spans = [];
                    for (let i = 0; i < num_samples; ++i)
                    {
                        let sample = data[i];
                        let x_coord = -Math.round(cell_width * (i + 0.5));
                        let sample_text_metrics = fontSizeCalcCanvas_ctx.measureText(sample);
                        let sample_text_height = sample_text_metrics.actualBoundingBoxAscent + sample_text_metrics.actualBoundingBoxDescent;
                        spans.push([x_coord + Math.round(sample_text_height / 2), x_coord - sample_text_height / 2]);
                    }

                    let not_overlapping = true;
                    for (let i = 0; i < spans.length - 1; ++i)
                    {
                        if (spans[i][1] - spans[i + 1][0] < 2)
                        {
                            not_overlapping = false;
                            break;
                        }
                    }

                    if (not_overlapping && (spans[0][0] < 0) && (spans[spans.length - 1][1] >= -(canvas_width - 1)))
                        break;

                    font_size -= 0.2;
                }

                d3.select('#heatmapLegendDiv').selectAll('*').remove();

                d3.select("#heatmapLegendDiv").append("canvas").attr("id", "heightCalcCanvas");
                let heightCalcCanvas = document.getElementById("heightCalcCanvas");
                let heightCalcCanvas_ctx = heightCalcCanvas.getContext("2d");
                heightCalcCanvas_ctx.font = `${font_size}px sans-serif`;

                for (let i = 0; i < num_samples; ++i)
                {
                    let sample = data[i];
                    let sample_text_height = heightCalcCanvas_ctx.measureText(sample).width;
                    if (height < sample_text_height)
                        height = sample_text_height;
                }

                height += 30;
            }

            height += 15;
            d3.select('#heatmapLegendDiv').selectAll('*').remove();

            d3.select("#heatmapLegendDiv").append("canvas")
                .attr("width", Math.ceil(width))
                .attr("height", Math.ceil(height))
                .attr("id", "heatmapLegendCanvas");
            let canvas = document.getElementById("heatmapLegendCanvas");
            let ctx = canvas.getContext("2d");
            ctx.font = `${font_size}px sans-serif`;
            ctx.textBaseline = "bottom";

            ctx.beginPath();

            if (!this.hide_isoform_heatmap_labels)
            {
                // Draw the horizontal axis line
                ctx.moveTo(0, 0);
                ctx.lineTo(canvas.width - 1, 0);

                // Draw the vertical ticks
                // for (let i = 0; i < num_samples; ++i)
                // {
                //     let x_coord = Math.round(cell_width * (i + 0.5));

                //     ctx.moveTo(x_coord, 0);
                //     ctx.lineTo(x_coord, 10);
                // }

                ctx.stroke();

                // Draw the sample names below the ticks
                ctx.save();
                ctx.rotate(Math.PI / 2);

                for (let i = 0; i < num_samples; ++i)
                {
                    let label = "";
                    if (i === 2) label = "CD34";
                    else if (i === 12) label = "SRSF2";
                    else if (i === 22) label = "U2AF1_S34F";                    
                    else if (i === 26) label = "U2AF1_Q157P";                    
                    else if (i === 28) label = "SF3B1";                    
                    else if (i === 39) label = "OtherAML";                    
                    
                    if (label) {
                        let sample_text_metrics = ctx.measureText(label);
                        let sample_text_height = sample_text_metrics.actualBoundingBoxAscent + sample_text_metrics.actualBoundingBoxDescent;
                        sample_text_height = sample_text_height*2;
                        let x_coord = -Math.round(cell_width * (i + 0.5)) + Math.round(sample_text_height / 2);
                        ctx.fillText(label, 18, x_coord);
                    }
                }

                ctx.restore();
            }
        },

        buildHeatmapLegendSvg(symbol = false)
        {
            if (!this.show_isoform_heatmap)
            {
                if (symbol)
                    return [-1, -1, null];
                return "";
            }

            let el = document.getElementById("heatmapDiv");
            if (!(el && this.heatmapData))
            {
                if (symbol)
                    return [-1, -1, null];
                return "";
            }

            let data = JSON.parse(JSON.stringify(this.heatmapData.samples));
            data.splice(this.heatmapData.transcript_id_colnum, 1);

            for (let i = 0; i < data.length; ++i)
            {
                let sample = data[i].toLowerCase();
                if (sample === "gene_id")
                {
                    data.splice(i, 1);
                    break;
                }
            }

            let padding = 16;
            let boundary = el.getBoundingClientRect();
            let width = boundary.width - 2 * padding;
            let height = 0;
            let font_size = 16.0;
            let canvas_width = Math.ceil(width);
            let num_samples = data.length;
            let cell_width = canvas_width / num_samples;

            d3.select("#heatmapLegendDiv").append("canvas").attr("id", "fontSizeCalcCanvas");
            let fontSizeCalcCanvas = document.getElementById("fontSizeCalcCanvas");
            let fontSizeCalcCanvas_ctx = fontSizeCalcCanvas.getContext("2d");

            if (!this.hide_isoform_heatmap_labels)
            {
                fontSizeCalcCanvas_ctx.textBaseline = "bottom";
                while (font_size > 2.0)
                {
                    fontSizeCalcCanvas_ctx.font = `${font_size}px sans-serif`;
                    let spans = [];
                    for (let i = 0; i < num_samples; ++i)
                    {
                        let sample = data[i];
                        let x_coord = -Math.round(cell_width * (i + 0.5));
                        let sample_text_metrics = fontSizeCalcCanvas_ctx.measureText(sample);
                        let sample_text_height = sample_text_metrics.actualBoundingBoxAscent + sample_text_metrics.actualBoundingBoxDescent;
                        spans.push([x_coord + Math.round(sample_text_height / 2), x_coord - sample_text_height / 2]);
                    }

                    let not_overlapping = true;
                    for (let i = 0; i < spans.length - 1; ++i)
                    {
                        if (spans[i][1] - spans[i + 1][0] < 1)
                        {
                            not_overlapping = false;
                            break;
                        }
                    }

                    if (not_overlapping && (spans[0][0] < 0) && (spans[spans.length - 1][1] >= -(canvas_width - 1)))
                        break;

                    font_size -= 0.1;
                }
            }

            let log_transform_enabled_font_size = 16.0;
            if (this.logTransform)
            {
                while (log_transform_enabled_font_size > 2.0)
                {
                    fontSizeCalcCanvas_ctx.font = `${log_transform_enabled_font_size}px sans-serif`;

                    let text_width = fontSizeCalcCanvas_ctx.measureText("(Log-transformed)").width;
                    if (svg_width - text_width >= 2)
                        break;

                    log_transform_enabled_font_size -= 0.1;
                }
            }

            document.querySelector('#fontSizeCalcCanvas').remove();

            d3.select("#heatmapLegendDiv").append("canvas").attr("id", "heightCalcCanvas");
            let heightCalcCanvas = document.getElementById("heightCalcCanvas");
            let heightCalcCanvas_ctx = heightCalcCanvas.getContext("2d");

            if (!this.hide_isoform_heatmap_labels)
            {
                heightCalcCanvas_ctx.font = `${font_size}px sans-serif`;

                for (let i = 0; i < num_samples; ++i)
                {
                    let sample = data[i];
                    let sample_text_height = heightCalcCanvas_ctx.measureText(sample).width;
                    if (height < sample_text_height)
                        height = sample_text_height;
                }

                height += 30;
            }

            height += 15 + 25;
            let svg_height = Math.ceil(height);

            let svg = "";

            if (!this.hide_isoform_heatmap_labels)
            {
                svg += line(0, 0, svg_width - 1, 0, "black", 1);

                // Draw the vertical ticks
                for (let i = 0; i < num_samples; ++i)
                {
                    let x_coord = Math.round(cell_width * (i + 0.5));
                    svg += line(x_coord, 0, x_coord, 5, "black", 1);
                }

                // Draw the sample names below the ticks
                for (let i = 0; i < num_samples; ++i)
                {
                    let label = "";
                    if (i === 3) label = "CD34";  // Position 3 (0-based index 2)
                    else if (i === 13) label = "SRSF2";
                    else if (i === 23) label = "U2AF1_S34F";                    
                    else if (i === 27) label = "U2AF1_Q157P";                    
                    else if (i === 29) label = "SF3B1";                    
                    else if (i === 40) label = "OtherAML";  
                    
                    if (label) {
                        let x_coord = Math.round(cell_width * (i + 0.5));
                        svg += heatmap_legend_text(label, x_coord, 9, font_size, "sans-serif");
                    }
                }
            }
            // let colour = {
            //     heatmapLow: '#1170aa', 
            //     heatmapMid: '#fff8e6', 
            //     heatmapHigh: '#fc7d0b', 
            //     invalid: '#c2c2c2'
            // };

            // // Draw the colour gradient
            // svg = linear_gradient("isoform_heatmap_legend_gradient", [["0%", colour.heatmapLow], ["50%", colour.heatmapMid], ["100%", colour.heatmapHigh]]) + svg;
            // svg += rect((svg_width - legendWidth) / 2, svg_height - 15 - 25, legendWidth, 15, "url(#isoform_heatmap_legend_gradient)");

            // // Draw the min/mid/max value labels
            // svg += text(min_label, (svg_width - legendWidth) / 2, svg_height, text_font_size, "sans-serif");
            // svg += text_centered(mid_label, svg_width / 2, svg_height, text_font_size, "sans-serif");
            // svg += text_right_aligned(max_label, (svg_width + legendWidth) / 2, svg_height, text_font_size, "sans-serif");

            if (this.logTransform)
            {
                heightCalcCanvas_ctx.font = `${log_transform_enabled_font_size}px sans-serif`;
                let log_transformed_text_metrics = heightCalcCanvas_ctx.measureText("(Log-transformed)");
                let log_transformed_text_height = Math.ceil(log_transformed_text_metrics.actualBoundingBoxAscent + log_transformed_text_metrics.actualBoundingBoxDescent);
                svg += text_centered("(Log-transformed)", svg_width / 2, svg_height + 40, log_transform_enabled_font_size, "sans-serif");
                svg_height += 40 + log_transformed_text_height;
            }

            document.querySelector('#heightCalcCanvas').remove();

            if (symbol)
                return [svg_width, svg_height, svg];

            svg = put_in_svg(svg_width, svg_height, svg);
            return svg;
        }
    },

    watch: {
        heatmapData: function() {
            this.buildHeatmapLegend();
        },
        show_isoform_heatmap: function() {
            this.buildHeatmapLegend();
        },
        hide_isoform_heatmap_labels: function() {
            this.buildHeatmapLegend();
        },
        logTransform: function() {
            this.buildHeatmapLegend();
        }
    }
}
</script>
