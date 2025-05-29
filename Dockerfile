FROM condaforge/miniforge3:24.11.3-2

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y emacs links less

#set up conda env
RUN conda create -n isovis
RUN echo "source activate isovis" > ~/.bashrc
ENV PATH=/opt/conda/envs/isovis/bin:$PATH

RUN conda install -c conda-forge nodejs=16

RUN mkdir /opt/isovis
WORKDIR /opt/isovis
COPY . /opt/isovis/

#install npm packages
RUN npm install -g npm@8
RUN npm install nuxt@2.15.8 
RUN npm install bootstrap-vue@2.23.1 d3@7.8.5 domain-gfx@0.2.0 svg-to-pdfkit@0.1.8 blob-stream@0.1.3 vuedraggable@2.24.3
RUN npm install --save-dev @babel/plugin-proposal-private-property-in-object

#apply needed edits to dep files
RUN sed -i.bck 's/height: this._computeHeight()/height: this._computeHeight(), spotlight: false/g' node_modules/domain-gfx/src/index.js
RUN sed -i.bck 's/font-family: Sans-Serif;/font-family: Sans-Serif;\n  z-index: 500;/g' node_modules/domain-gfx/src/tooltip/style.js

# Clear nuxt cache and temporary files
RUN rm -rf .nuxt node_modules/.cache

ENV NODE_OPTIONS=--openssl-legacy-provider
ENV HOST=0.0.0.0
ENV PORT=8080
EXPOSE 8080

RUN npm run build

CMD ["npm", "run", "start"]
