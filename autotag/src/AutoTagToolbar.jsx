import React from 'react';
import Range from 'react-range';

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
      <div style={{position:'absolute',
                   top:'0px',
                   left:'0px',
                   right:'0px',
                   height: '29px',
                   borderRight:'0px'}} className={'toolbar'}>

        Show unmapped: <input type="checkbox"
                              checked={this.props.showUnmapped}
                              onChange={this.toggleUnmapped} />

        {
          this.props.showUnmapped &&
          <span>
            <strong>{this.props.requiredTokenCardinality}</strong>
            <Range className='slider'
                   onChange={this.handleChangeRequiredTokenCardinality}
                   type='range'
                   value={this.props.requiredTokenCardinality}
                   min={1}
                   max={this.props.maxTokenCardinality} />
          </span>
        }

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
