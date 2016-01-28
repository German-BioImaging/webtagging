import React from 'react';
import Range from 'react-range';
import ReactTooltip from 'react-tooltip';

export default class AutoTagToolbar extends React.Component {

  constructor() {
    super();

    // Prebind this to callback methods
    this.refreshForm = this.refreshForm.bind(this);
    this.toggleUnmapped = this.toggleUnmapped.bind(this);
    this.handleChangeRequiredTokenCardinality = this.handleChangeRequiredTokenCardinality.bind(this);

  }

  refreshForm(e) {
    e.preventDefault();
    this.props.refreshForm();
  }

  toggleUnmapped(e) {
    this.props.toggleUnmapped();
  }

  handleChangeRequiredTokenCardinality(e) {
    this.props.handleChangeRequiredTokenCardinality(e.target.value);
  }

  render() {
    return (
      <div
        style={{
          position: 'absolute',
          top: '5px',
          left: '0px',
          right: '0px',
          height: '29px',
          marginRight: '10px'
        }}
        className={'toolbar'}
      >

        <span
          style={{
            float: 'left',
            marginLeft: '20px',
            fontSize: '12px',
            fontWeight: 'bold'
          }}
        >
        {
          this.props.showUnmapped &&
          <span>
            <span data-tip data-for={'tooltip-toolbar-slider'} style={{marginRight: '10px'}}>Rarity Threshold</span>
            {this.props.requiredTokenCardinality}
            <Range className='slider'
                   onChange={this.handleChangeRequiredTokenCardinality}
                   type='range'
                   value={this.props.requiredTokenCardinality}
                   min={1}
                   max={this.props.maxTokenCardinality}
                   style={{marginLeft: '10px', marginTop: '-1px', position: 'relative', bottom: '-3px'}} />
          </span>
        }
        </span>

        <ReactTooltip id={'tooltip-toolbar-slider'} place="bottom" type="dark" effect="float">
          Hide columns if token is found on fewer than this number of images
        </ReactTooltip>

        <span
          data-tip
          data-for={'tooltip-toolbar-show-all'}
          style={{fontSize: '12px', fontWeight: 'bold'}}
        >
          Show All Potential Tags
        </span>

        <ReactTooltip id={'tooltip-toolbar-show-all'} place="bottom" type="dark" effect="float">
          Show all the tokens found in the filenames that do not match an existing tag
        </ReactTooltip>

        <input type="checkbox"
               checked={this.props.showUnmapped}
               onChange={this.toggleUnmapped} />

        <input type="submit"
               id="applyButton"
               value="Apply" />

        <input type="button"
               onClick={this.refreshForm}
               id="refreshForm"
               value="Refresh" />

      </div>
    );
  }
}
