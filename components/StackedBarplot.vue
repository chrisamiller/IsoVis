/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

Component to render a stacked barplot of isoform abundance fractions or absolute CPM per sample.
Opened via $root event 'showStackedBarplot'. Receives heatmapData as a prop.

<template>
<b-modal v-model="modalVisible" size="xl" title="Abundance Barplot"
         hide-footer scrollable>
  <div class="d-flex align-items-center mb-2" style="gap:8px; flex-wrap:wrap;">
    <span style="font-size:13px; font-weight:600;">View:</span>
    <b-button-group size="sm">
      <b-button :variant="!absoluteMode ? 'primary' : 'outline-secondary'"
                @click="setMode(false)">Relative abundance</b-button>
      <b-button :variant="absoluteMode ? 'primary' : 'outline-secondary'"
                @click="setMode(true)">Actual abundance (CPM)</b-button>
    </b-button-group>
    <b-button size="sm" variant="outline-secondary" @click="exportPng">Export PNG</b-button>
  </div>
  <div id="stackedBarplotDiv" style="overflow-x:auto; position:relative;"></div>
</b-modal>
</template>

<script>
import * as d3 from 'd3';
import { BModal, BButton, BButtonGroup } from 'bootstrap-vue';

export default {
    props: ["heatmapData"],

    components: { BModal, BButton, BButtonGroup },

    data: () => ({ modalVisible: false, absoluteMode: false }),

    mounted() {
        this.$root.$on('showStackedBarplot', () => { this.modalVisible = true; });
    },

    beforeDestroy() {
        this.$root.$off('showStackedBarplot');
    },

    watch: {
        modalVisible(val) {
            if (val) this.$nextTick(() => this.buildBarplot());
        },
        absoluteMode() {
            if (this.modalVisible) this.$nextTick(() => this.buildBarplot());
        }
    },

    methods: {
        setMode(absolute) {
            this.absoluteMode = absolute;
        },

        exportPng() {
            const svgEl = document.querySelector('#stackedBarplotDiv svg');
            if (!svgEl) return;

            const width = svgEl.getAttribute('width');
            const height = svgEl.getAttribute('height');

            // Serialize SVG with explicit white background
            const clone = svgEl.cloneNode(true);
            const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            bg.setAttribute('width', width);
            bg.setAttribute('height', height);
            bg.setAttribute('fill', 'white');
            clone.insertBefore(bg, clone.firstChild);
            clone.querySelectorAll('text').forEach(t => t.setAttribute('font-family', 'sans-serif'));

            const serialized = new XMLSerializer().serializeToString(clone);
            const blob = new Blob([serialized], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(blob);

            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const scale = 2; // 2× for retina-quality output
                canvas.width = width * scale;
                canvas.height = height * scale;
                const ctx = canvas.getContext('2d');
                ctx.scale(scale, scale);
                ctx.drawImage(img, 0, 0);
                URL.revokeObjectURL(url);

                const a = document.createElement('a');
                const mode = this.absoluteMode ? 'cpm' : 'relative';
                a.download = `abundance_barplot_${mode}.png`;
                a.href = canvas.toDataURL('image/png');
                a.click();
            };
            img.src = url;
        },

        buildBarplot() {
            const container = document.getElementById('stackedBarplotDiv');
            if (!container) return;
            d3.select('#stackedBarplotDiv').selectAll('*').remove();

            if (!this.heatmapData || !this.heatmapData.export || !this.heatmapData.export.length) {
                container.textContent = 'No data available';
                return;
            }

            // --- 1. Get ordered sample list (same filtering as Heatmap.vue) ---
            let samples = JSON.parse(JSON.stringify(this.heatmapData.samples));
            samples.splice(this.heatmapData.transcript_id_colnum, 1);
            for (let i = 0; i < samples.length; ++i) {
                if (samples[i].toLowerCase() === 'gene_id') {
                    samples.splice(i, 1);
                    break;
                }
            }

            // --- 2. Build value map: dataMap[transcript][sample] = value ---
            const dataMap = {};
            for (const { transcript, sample, value } of this.heatmapData.export) {
                if (!dataMap[transcript]) dataMap[transcript] = {};
                dataMap[transcript][sample] = value;
            }

            // --- 3. Per-transcript global totals ---
            const transcriptTotals = {};
            let grandTotal = 0;
            for (const tx of Object.keys(dataMap)) {
                let txSum = 0;
                for (const s of samples) {
                    txSum += dataMap[tx][s] || 0;
                }
                transcriptTotals[tx] = txSum;
                grandTotal += txSum;
            }

            if (grandTotal === 0) {
                container.textContent = 'No data available';
                return;
            }

            // --- 4. Split transcripts into named (≥1% globally) and pooled ---
            const namedTranscripts = [];
            const pooledTranscripts = [];
            for (const tx of Object.keys(transcriptTotals)) {
                if (transcriptTotals[tx] / grandTotal >= 0.01) {
                    namedTranscripts.push(tx);
                } else {
                    pooledTranscripts.push(tx);
                }
            }
            namedTranscripts.sort((a, b) => transcriptTotals[b] - transcriptTotals[a]);

            const hasOther = pooledTranscripts.length > 0;
            const stackKeys = hasOther ? [...namedTranscripts, 'other_tx'] : [...namedTranscripts];

            // --- 5. Build per-sample rows for D3 stack ---
            const rows = samples.map(s => {
                const row = { sample: s };
                if (this.absoluteMode) {
                    // Absolute: raw CPM values
                    for (const tx of namedTranscripts) {
                        row[tx] = dataMap[tx][s] || 0;
                    }
                    if (hasOther) {
                        let otherSum = 0;
                        for (const tx of pooledTranscripts) otherSum += dataMap[tx][s] || 0;
                        row['other_tx'] = otherSum;
                    }
                } else {
                    // Relative: fractions summing to 1
                    let denom = 0;
                    for (const tx of Object.keys(dataMap)) denom += dataMap[tx][s] || 0;
                    if (denom === 0) {
                        for (const key of stackKeys) row[key] = 0;
                    } else {
                        for (const tx of namedTranscripts) {
                            row[tx] = (dataMap[tx][s] || 0) / denom;
                        }
                        if (hasOther) {
                            let otherSum = 0;
                            for (const tx of pooledTranscripts) otherSum += dataMap[tx][s] || 0;
                            row['other_tx'] = otherSum / denom;
                        }
                    }
                }
                return row;
            });

            // --- D3 rendering ---
            const marginTop = 40, marginRight = 20, marginLeft = 60;
            const labelAreaHeight = 120;
            const marginBottom = 8 + labelAreaHeight;
            const legendWidth = 230;
            const containerWidth = container.clientWidth || 900;
            const plotWidth = containerWidth - marginLeft - marginRight - legendWidth;
            const plotHeight = 450;
            const totalWidth = containerWidth;
            const totalHeight = plotHeight + marginTop + marginBottom;

            const xScale = d3.scaleBand()
                .domain(samples)
                .range([0, plotWidth])
                .padding(0.05);

            // Y scale: 0-1 for relative, 0-max sample total for absolute
            let yMax = 1;
            if (this.absoluteMode) {
                yMax = d3.max(rows, row => {
                    let sum = 0;
                    for (const key of stackKeys) sum += row[key] || 0;
                    return sum;
                }) || 1;
            }

            const yScale = d3.scaleLinear()
                .domain([0, yMax])
                .range([plotHeight, 0])
                .nice();

            const colorScale = d3.scaleOrdinal(d3.schemeTableau10)
                .domain(namedTranscripts);

            const getColor = key => key === 'other_tx' ? '#aaaaaa' : colorScale(key);

            const series = d3.stack().keys(stackKeys)(rows);

            const svg = d3.select('#stackedBarplotDiv')
                .append('svg')
                .attr('width', totalWidth)
                .attr('height', totalHeight);

            const plot = svg.append('g')
                .attr('transform', `translate(${marginLeft},${marginTop})`);

            // Tooltip div
            const tooltip = d3.select('#stackedBarplotDiv')
                .append('div')
                .style('position', 'absolute')
                .style('background', 'rgba(0,0,0,0.75)')
                .style('color', '#fff')
                .style('padding', '4px 8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('display', 'none');

            const isAbsolute = this.absoluteMode;

            // Bars
            plot.selectAll('g.layer')
                .data(series)
                .join('g')
                .attr('class', 'layer')
                .attr('fill', d => getColor(d.key))
                .selectAll('rect')
                .data(d => d)
                .join('rect')
                .attr('x', d => xScale(d.data.sample))
                .attr('y', d => yScale(d[1]))
                .attr('height', d => yScale(d[0]) - yScale(d[1]))
                .attr('width', xScale.bandwidth())
                .on('mouseover', (event, d) => {
                    const key = d3.select(event.target.parentNode).datum().key;
                    const segValue = d[1] - d[0];
                    const valStr = isAbsolute
                        ? `CPM: ${segValue.toFixed(2)}`
                        : `Fraction: ${(segValue * 100).toFixed(1)}%`;
                    const displayKey = key === 'other_tx' ? 'Other Tx (<1% abundance)' : key;
                    tooltip
                        .style('display', 'block')
                        .html(`Sample: ${d.data.sample}<br>Transcript: ${displayKey}<br>${valStr}`);
                })
                .on('mousemove', event => {
                    const rect = container.getBoundingClientRect();
                    tooltip
                        .style('left', (event.clientX - rect.left + 12) + 'px')
                        .style('top', (event.clientY - rect.top - 28) + 'px');
                })
                .on('mouseleave', () => tooltip.style('display', 'none'));

            // Y axis
            const yAxis = isAbsolute
                ? d3.axisLeft(yScale).ticks(8).tickFormat(d3.format(',.0f'))
                : d3.axisLeft(yScale).tickFormat(d3.format('.0%'));
            plot.append('g').call(yAxis);

            // Y axis label
            const yLabel = isAbsolute ? 'CPM' : 'Relative abundance';
            svg.append('text')
                .attr('transform', `rotate(-90)`)
                .attr('x', -(marginTop + plotHeight / 2))
                .attr('y', 14)
                .attr('text-anchor', 'middle')
                .attr('font-size', 11)
                .text(yLabel);

            // X axis (no tick labels)
            plot.append('g')
                .attr('transform', `translate(0,${plotHeight})`)
                .call(d3.axisBottom(xScale).tickFormat(''));

            // Group dividers
            const dividers = this.heatmapData.columnDividers || [];
            for (const colIndex of dividers) {
                if (colIndex < samples.length) {
                    const x = xScale(samples[colIndex]);
                    if (x !== undefined) {
                        plot.append('line')
                            .attr('x1', x).attr('x2', x)
                            .attr('y1', 0).attr('y2', plotHeight + labelAreaHeight)
                            .attr('stroke', '#555')
                            .attr('stroke-width', 1);
                    }
                }
            }

            // Group labels
            const groups = this.heatmapData.groups || [];
            for (const g of groups) {
                if (g.midpoint < samples.length) {
                    const xStart = xScale(samples[g.start]) || 0;
                    const xEnd = (xScale(samples[g.end]) || 0) + xScale.bandwidth();
                    const cx = (xStart + xEnd) / 2;
                    const cy = plotHeight + labelAreaHeight / 2;
                    plot.append('text')
                        .attr('x', cx)
                        .attr('y', cy)
                        .attr('text-anchor', 'middle')
                        .attr('dominant-baseline', 'middle')
                        .attr('font-size', 11)
                        .attr('transform', `rotate(-90, ${cx}, ${cy})`)
                        .text(g.name);
                }
            }

            // Legend
            const legendG = svg.append('g')
                .attr('transform', `translate(${marginLeft + plotWidth + 15},${marginTop})`);

            legendG.append('text')
                .attr('x', 0).attr('y', 0)
                .attr('font-size', 12)
                .attr('font-weight', 'bold')
                .text('Transcripts');

            stackKeys.forEach((key, i) => {
                const y = 18 + i * 18;
                legendG.append('rect')
                    .attr('x', 0).attr('y', y - 12)
                    .attr('width', 12).attr('height', 12)
                    .attr('fill', getColor(key));

                const displayKey = key === 'other_tx' ? 'Other Tx (<1% abundance)' : key;
                const label = displayKey.length > 28 ? displayKey.slice(0, 27) + '…' : displayKey;
                legendG.append('text')
                    .attr('x', 16).attr('y', y - 1)
                    .attr('font-size', 11)
                    .text(label);
            });
        }
    }
}
</script>
