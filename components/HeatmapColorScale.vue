/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

<template>
<div>
    <div id="heatmapColorScaleDiv">
    </div>
</div>
</template>

<script>
import * as d3 from 'd3';
import {put_in_svg, rect, linear_gradient, text, text_centered, text_right_aligned} from "~/assets/svg_utils";

export default {
    props: ["heatmapData", "logTransform"],
    data: () => {
        return {
            show_isoform_heatmap: true
        };
    },

    methods: {
        buildColorScale() {
            // Clear the space of any content
            d3.select('#heatmapColorScaleDiv').selectAll('*').remove();

            if (!this.show_isoform_heatmap)
                return;

            let el = document.getElementById("heatmapDiv");
            if (!(el && this.heatmapData)) return;

            let padding = 16;
            let boundary = el.getBoundingClientRect();
            let width = boundary.width - 2 * padding;
            let colour = {
                heatmapLow: '#1170aa',
                heatmapMid: '#fff8e6',
                heatmapHigh: '#fc7d0b',
                invalid: '#c2c2c2'
            };

            let height = 40; // Just enough for the color bar and labels
            let canvas_width = Math.ceil(width);

            d3.select("#heatmapColorScaleDiv").append("canvas")
                .attr("width", canvas_width)
                .attr("height", height)
                .attr("id", "heatmapColorScaleCanvas");
            let canvas = document.getElementById("heatmapColorScaleCanvas");
            let ctx = canvas.getContext("2d");

            // Draw the colour gradient
            let legendWidth = canvas.width / 1.5;
            let gradient = ctx.createLinearGradient((canvas.width - legendWidth) / 2, 0, (canvas.width + legendWidth) / 2, 0);
            gradient.addColorStop(0, colour.heatmapLow);
            gradient.addColorStop(0.5, colour.heatmapMid);
            gradient.addColorStop(1, colour.heatmapHigh);

            ctx.save();
            ctx.fillStyle = gradient;
            ctx.fillRect((canvas.width - legendWidth) / 2, 0, legendWidth, 15);
            ctx.restore();

            // text formatting for min/max/avg value labels
            let getLabel = (val) => {
                if (val === undefined)
                    return "NaN";
                val = Number.isInteger(val) ? val.toFixed() : val.toFixed(2);
                if (val.length > 1 && val.split('.')[1] == '00')
                    val = val.split('.')[0];
                if (val > 2){
                    return Math.round(val);
                } else {
                    return val;
                }
            }

            // add and position labels to legend
            let min = this.logTransform ? this.heatmapData.logMin : this.heatmapData.minValue;
            let max = this.logTransform ? this.heatmapData.logMax : this.heatmapData.maxValue;
            // let mid = this.logTransform ? this.heatmapData.logAverage : this.heatmapData.average;
            let mid = min+((max-min)/2); //use midpoint between min/man (not average)

            let min_label = getLabel(min);
            let mid_label = getLabel(mid);
            let max_label = getLabel(max);

            let font_size = 16.0;
            let min_label_end, mid_label_start, mid_label_end, mid_label_width, max_label_start, max_label_width;

            while (font_size > 2.0) {
                ctx.font = `${font_size}px sans-serif`;

                min_label_end = ((canvas.width - legendWidth) / 2) + ctx.measureText(min_label).width;
                max_label_start = ((canvas.width + legendWidth) / 2) - ctx.measureText(max_label).width;
                max_label_width = ctx.measureText(max_label).width;

                mid_label_width = ctx.measureText(mid_label).width;
                mid_label_start = (canvas.width - mid_label_width) / 2;
                mid_label_end = (canvas.width + mid_label_width) / 2;

                if ((mid_label_start - min_label_end >= 5) && (max_label_start - mid_label_end >= 5))
                    break;

                font_size -= 0.1;
            }

            ctx.fillText(min_label, (canvas.width - legendWidth) / 2, height);
            ctx.fillText(mid_label, mid_label_start, height);
            ctx.fillText(max_label, max_label_start, height);
            if(this.logTransform){
                ctx.fillText("(log2)", max_label_start + max_label_width*1.3, height/3);
            }
        }
    },

    watch: {
        heatmapData: function() {
            this.buildColorScale();
        },
        show_isoform_heatmap: function() {
            this.buildColorScale();
        },
        logTransform: function() {
            this.buildColorScale();
        }
    }
}
</script> 
