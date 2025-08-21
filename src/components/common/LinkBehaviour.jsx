// src/components/common/LinkBehaviour.jsx
import * as React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import PropTypes from 'prop-types';

/**
 * Custom Link component that integrates MUI with React Router
 * This component is used in the theme configuration to enable MUI Links to work with React Router
 */
const LinkBehavior = React.forwardRef(function LinkBehavior(props, ref) {
    const { href, ...other } = props;

    // Map MUI's href prop to react-router's to prop
    return (
        <RouterLink
            ref={ref}
            to={href || '#'}
            {...other}
        />
    );
});

LinkBehavior.propTypes = {
    href: PropTypes.string,
};

export default LinkBehavior;